#include <iostream>
#include <fstream>
#include <cxxopts.hpp>
#include <ultimaille/all.h>

#include "collections.h"
#include "paths.h"
#include "parameters.h"
#include "date_time.h"
#include "cxxopts_ParseResult_custom.h"
#include "graphite_script.h"
#include "info_file.h"
#include "user_confirmation.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Compute a labeling with a graph-cut optimization algorithm");
    options
        .set_width(80)
        .positional_help("<input> [output] [compactness] [fidelity]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("compactness", "Compactness coefficient for the graph-cut optimisation", cxxopts::value<std::string>()->default_value("1"),"VALUE")
            ("fidelity", "Fidelity coefficient for the graph-cut optimisation", cxxopts::value<std::string>()->default_value("3"),"VALUE")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("o,output", "Name of the output folder(s) to create. \%c is replaced by the compactness, \%f by the fidelity and \%d by the date and time", cxxopts::value<std::string>()->default_value("graphcut_\%c_\%f"),"NAME");
    options.parse_positional({"input","output","compactness","fidelity"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input"});
    result.require_not_empty({"output","compactness","fidelity"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);
    std::string output_folder_name = result["output"];
    bool write_output_collections = !result.is_specified("no-output-collections");

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(GENOMESH);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_2_TETRA_MESH,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_graphcut_" + global_beginning.filename_string() : //if the input is a collection
                            "graphcut_labeling"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("graphcut_labeling",global_beginning.pretty_string(),result["comments"]);

    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%c"), result["compactness"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%f"), result["fidelity"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%d"), global_beginning.filename_string());

    std::string cmd;
    int returncode = 0;
    special_case_policy overwrite_policy = ask;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;
        
        //check if all the input files exist
        if(missing_files_among({
            input_folder / SURFACE_OBJ_FILE,
            input_folder / TRIANGLE_TO_TETRA_FILE
        },path_list[WORKING_DATA_FOLDER])) {
            returncode = 1;//do not open Graphite in case of single input
            std::cout << "Missing files" << std::endl;
            output_collections.error_cases->new_comments("missing input files");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }
        
        //check if the output files already exist. if so, ask for confirmation
        bool additional_printing = (overwrite_policy==ask);
        if(existing_files_among({
            input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE,
            input_folder / output_folder_name / PER_TETRA_FACES_LABELING_FILE,
            input_folder / output_folder_name / LABELING_STATS_FILE,
            input_folder / output_folder_name / TURNING_POINTS_OBJ_FILE,
            input_folder / output_folder_name / INFO_JSON_FILE,
            input_folder / output_folder_name / LABELED_SURFACE_GEOGRAM_FILE
            //other files (logs.txt, lua script) are not important
        },path_list[WORKING_DATA_FOLDER],additional_printing)) {
            bool user_wants_to_overwrite = ask_for_confirmation("\t-> Are you sure you want to overwrite these files ?",overwrite_policy);
            if(additional_printing) std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;//re-print the input name
            if(user_wants_to_overwrite==false) {
                returncode = 1;//do not open Graphite in case of single input
                std::cout << "Canceled" << std::endl;
                continue;
            }
        }

        std::filesystem::create_directory(input_folder / output_folder_name);//create the output folder

        std::ofstream txt_logs(input_folder / output_folder_name / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / output_folder_name / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|   graphcut_labeling   |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[GENOMESH] / "graphcut_labeling").string() + " " +
              (input_folder / TRIANGLE_TO_TETRA_FILE).string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              result["compactness"] + " " +
              result["fidelity"] + " " +
              (input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / output_folder_name / PER_TETRA_FACES_LABELING_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during graphcut_labeling call");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        //evaluate the labeling and get scores and stats (nb charts, fidelity, turning-points...)

        cmd = (path_list[GENOMESH] / "labeling_stats").string() + " " +
              (input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name / LABELING_STATS_FILE).string() + " " +
              (input_folder / output_folder_name / TURNING_POINTS_OBJ_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        returncode = system(cmd.c_str());

        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during labeling_stats call");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder / output_folder_name);

        LabelingInfo info(input_folder / output_folder_name / INFO_JSON_FILE);
        info.generated_by("graphcut_labeling");
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
        info.fill_from(input_folder / output_folder_name / LABELING_STATS_FILE);
        info.compactness_of("graphcut_labeling",std::stoi(result["compactness"]));
        info.fidelity_of("graphcut_labeling",std::stoi(result["fidelity"]));

        //with Ultimaille, load the surface mesh and the just-computed labeling
        UM::Triangles surface;
        UM::read_by_extension( (input_folder / SURFACE_OBJ_FILE).string() , surface);
        UM::FacetAttribute<int> labeling(surface);
        //fill labeling
        std::ifstream ifs(input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE);
        if(ifs.is_open()) {
            int label, face_number = 0;
            while (ifs >> label) {
                labeling[face_number] = label;
                face_number++;
            }
            ifs.close();

            //write a .geogram file with the surface mesh + labeling, named "attr", as UM::SurfaceAttributes
            //inspired by Trace::drop_facet_scalar()
            UM::write_by_extension( (input_folder / output_folder_name / LABELED_SURFACE_GEOGRAM_FILE).string() , surface, UM::SurfaceAttributes{ {}, { { "attr", labeling.ptr } }, {} });

            //then create a Lua script for Graphite
            GraphiteScript graphite_script(input_folder / output_folder_name / LABELED_SURFACE_LUA_SCRIPT, path_list);
            graphite_script.add_comments("generated by the graphcut_labeling wrapper of shared-polycube-pipeline");
            graphite_script.add_comments(current_input_beginning.pretty_string());
            graphite_script.hide_text_editor();
            graphite_script.load_object(LABELED_SURFACE_GEOGRAM_FILE);
            graphite_script.set_mesh_style(true,0.0f,0.0f,0.0f,1);
            graphite_script.set_painting_on_attribute("facets.attr","french",0.0f,5.0f,false);
            graphite_script.set_lighting(false);
            graphite_script.load_object(TURNING_POINTS_OBJ_FILE);
            graphite_script.set_vertices_style(true,1.0f,1.0f,0.0f,5);
        }
        // TODO else, write that the PER_SURFACE_TRIANGLE_LABELING_FILE could not be opened in STD_PRINTINGS_FILE
    }

    // in case of a single input folder, open the labeling with Graphite
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        // TODO check if LABELED_SURFACE_LUA_SCRIPT and GRAPHITE_BASH_SCRIPT were successfully created
        cmd = "cd " + (*input_folders.begin() / output_folder_name).string() + " && ./" + GRAPHITE_BASH_SCRIPT + " > /dev/null";//silent output
        system(cmd.c_str());
    }
#endif

    return 0;
}