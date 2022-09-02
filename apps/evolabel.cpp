#include <iostream>
#include <fstream>
#include <filesystem>
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

#ifdef UNMODIFIED_EVOLABEL
    cxxopts::Options options(argv[0], "Apply the Evocube genetic labeling framework");
#else
    cxxopts::Options options(argv[0], "Apply the tweaked Evocube genetic labeling framework");
#endif
    options
        .set_width(80)
        .positional_help("<input> [output]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
#ifdef UNMODIFIED_EVOLABEL
            ("o,output", "Name of the output folder(s) to create. \%d is replaced by the date and time", cxxopts::value<std::string>()->default_value("evolabel_\%d"),"NAME")
#else
            ("o,output", "Name of the output folder(s) to create. \%d is replaced by the date and time", cxxopts::value<std::string>()->default_value("evolabel_tweaked_\%d"),"NAME")
#endif
            ("v,version", "Print the version (date of last modification) of the underlying executables");
    options.parse_positional({"input","output"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(EVOCUBE_TWEAKS);

    //parse results
#ifdef UNMODIFIED_EVOLABEL
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[EVOCUBE_TWEAKS] / "evolabel" });
#else
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[EVOCUBE_TWEAKS] / "evolabel_tweaked" });
#endif
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
#ifdef UNMODIFIED_EVOLABEL
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_evolabel_" + global_beginning.filename_string() : //if the input is a collection
                            "evolabel"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("evolabel",global_beginning.pretty_string(),result["comments"]);
#else
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_evolabeltweaked_" + global_beginning.filename_string() : //if the input is a collection
                            "evolabel_tweaked"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("evolabel",global_beginning.pretty_string(),result["comments"]);
#endif

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
            //original output files of evocube/evolabel
            input_folder / output_folder_name / "labeling.txt",
            input_folder / output_folder_name / "labeling_init.txt",
            input_folder / output_folder_name / "labeling_on_tets.txt",
            input_folder / output_folder_name / "logs.json",
            input_folder / output_folder_name / "fast_polycube_surf.obj",
            input_folder / output_folder_name / TURNING_POINTS_OBJ_FILE,
            //renamed output files
            input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE,
            input_folder / output_folder_name / PER_TETRA_FACETS_LABELING_FILE,
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
#ifdef UNMODIFIED_EVOLABEL
        txt_logs << "\n|       evolabel        |";
#else
        txt_logs << "\n|   evolabel_tweaked    |";
#endif
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

#ifdef UNMODIFIED_EVOLABEL
        cmd = (path_list[EVOCUBE_TWEAKS] / "evolabel").string() + " " +
#else
        cmd = (path_list[EVOCUBE_TWEAKS] / "evolabel_tweaked").string() + " " +
#endif
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
#ifdef UNMODIFIED_EVOLABEL
            output_collections.error_cases->new_comments("error during evolabel call");
#else
            output_collections.error_cases->new_comments("error during evolabel_tweaked call");
#endif
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder / output_folder_name);

        //rename output files
        std::filesystem::rename(
            input_folder / output_folder_name / "labeling.txt",
            input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE );
        std::filesystem::rename(
            input_folder / output_folder_name / "labeling_on_tets.txt",
            input_folder / output_folder_name / PER_TETRA_FACETS_LABELING_FILE );

        //copy labeling stats (nb charts, fidelity, turning-points...) from logs.json to info.json

        LabelingInfo info(input_folder / output_folder_name / INFO_JSON_FILE);
#ifdef UNMODIFIED_EVOLABEL
        info.generated_by("evolabel");
#else
        info.generated_by("evolabel_tweaked");
#endif
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
#ifdef UNMODIFIED_EVOLABEL
        info.fill_from(input_folder / output_folder_name / "logs.json",false);
#else
        info.fill_from(input_folder / output_folder_name / "logs.json",true);
#endif
        
        //then (re)generate the Lua script for Graphite
#ifdef UNMODIFIED_EVOLABEL
        regenerate_Graphite_visu(path_list[WORKING_DATA_FOLDER],input_folder,current_input_beginning,"the evolabel wrapper");
#else
        regenerate_Graphite_visu(path_list[WORKING_DATA_FOLDER],input_folder,current_input_beginning,"the evolabel_tweaked wrapper");
#endif
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