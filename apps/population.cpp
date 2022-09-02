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

    cxxopts::Options options(argv[0], "Compute a labeling with the 2021 Evocube algorithm (hexercise)");
    options
        .set_width(80)
        .positional_help("<input> [output]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("o,output", "Name of the output folder(s) to create. \%d is replaced by the date and time", cxxopts::value<std::string>()->default_value("population"),"NAME")//no %d by default because population is currently deterministic
            ("v,version", "Print the version (date of last modification) of the underlying executables");
    options.parse_positional({"input","output"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(GENOMESH);
    path_list.require(FASTBNDPOLYCUBE);

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[GENOMESH] / "population", path_list[GENOMESH] / "labeling_stats", path_list[FASTBNDPOLYCUBE] / "fastpolycube" });
    result.require({"input"});
    result.require_not_empty({"output"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);
    std::string output_folder_name = result["output"];
    bool write_output_collections = !result.is_specified("no-output-collections");

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_2_TETRA_MESH,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_population_" + global_beginning.filename_string() : //if the input is a collection
                            "population"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("population",global_beginning.pretty_string(),result["comments"]);

    //format the output folder name
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
            input_folder / output_folder_name / PER_TETRA_FACETS_LABELING_FILE,
            input_folder / output_folder_name / LABELING_STATS_FILE,
            input_folder / output_folder_name / TURNING_POINTS_OBJ_FILE,
            input_folder / output_folder_name / INFO_JSON_FILE,
            input_folder / output_folder_name / LABELED_SURFACE_GEOGRAM_FILE,
            input_folder / output_folder_name / FAST_SURFACE_POLYCUBE_OBJ_FILE,
            input_folder / output_folder_name / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE
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
        txt_logs << "\n|      population       |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[GENOMESH] / "population").string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / TRIANGLE_TO_TETRA_FILE).string() + " " +
              (input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / output_folder_name / PER_TETRA_FACETS_LABELING_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during population call");
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

        //generate a surface polycube from the labeling

        cmd = (path_list[FASTBNDPOLYCUBE] / "fastpolycube").string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / output_folder_name / FAST_SURFACE_POLYCUBE_OBJ_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());

        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during fastpolycube call");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder / output_folder_name);

        LabelingInfo info(input_folder / output_folder_name / INFO_JSON_FILE);
        info.generated_by("population");
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
        info.fill_from(input_folder / output_folder_name / LABELING_STATS_FILE);

        //then (re)generate the Lua script for Graphite
        regenerate_Graphite_visu(path_list[WORKING_DATA_FOLDER],input_folder / output_folder_name,current_input_beginning,"the population wrapper");
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