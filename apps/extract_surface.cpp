#include <iostream>
#include <fstream>
#include <cxxopts.hpp>

#include "collections.h"
#include "paths.h"
#include "trace.h"
#include "parameters.h"
#include "date_time.h"
#include "cxxopts_ParseResult_custom.h"
#include "user_confirmation.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Extract the triangular surface of a tetrahedral mesh");
    options
        .set_width(80)
        .positional_help("<input>")
        .show_positional_help()
        .add_options()
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH");
    options.parse_positional({"input"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(GENOMESH);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(normalized_trimed(result["input"]),path_list[WORKING_DATA_FOLDER],DEPTH_2_TETRA_MESH,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    std::string cmd;
    int returncode = 0;
    special_case_policy overwrite_policy = ask;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;

        //check if all the input files exist
        if(missing_files_among({
            input_folder / TETRA_MESH_FILE
        },path_list[WORKING_DATA_FOLDER])) {
            returncode = 1;//do not open Graphite in case of single input
            std::cout << "Missing files" << std::endl;
            continue;
        }
        
        //check if the output files already exist. if so, ask for confirmation
        bool additional_printing = (overwrite_policy==ask);
        if(existing_files_among({
            input_folder / SURFACE_OBJ_FILE,
            input_folder / TRIANGLE_TO_TETRA_FILE
        },path_list[WORKING_DATA_FOLDER],additional_printing)) {
            bool user_wants_to_overwrite = ask_for_confirmation("\t-> Are you sure you want to overwrite these files ?",overwrite_policy);
            if(additional_printing) std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;//re-print the input name
            if(user_wants_to_overwrite==false) {
                returncode = 1;//do not open Graphite in case of single input
                std::cout << "Canceled" << std::endl;
                continue;
            }
            else {
                //because tris_to_tets has not the same behaviour if SURFACE_OBJ_FILE exists,
                //make sure it does not exists
                std::filesystem::remove(input_folder / SURFACE_OBJ_FILE);
            }
        }

        std::ofstream txt_logs(input_folder / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        //add a separator between the existing printings of step2mesh and the ones of extract_surface

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|    extract_surface    |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[GENOMESH] / "tris_to_tets").string() + " " +
              (input_folder / TETRA_MESH_FILE).string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / TRIANGLE_TO_TETRA_FILE).string() +
              " &>> " + (input_folder / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the logs of step2mesh)
        returncode = system(cmd.c_str());
        std::cout << ( (returncode!=0) ? "Error" : "Done") << std::endl;
    }

    // TODO write a collections with failed cases

    //in case of a single input folder, open the surface mesh with Graphite
    //TODO modif (or replace) Trace to put the lua script in the output folder, not in build
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        path_list.require(GRAPHITE,false);
        Trace::initialize(path_list[GRAPHITE]);
        UM::Triangles m;
        UM::read_by_extension((*input_folders.begin() / SURFACE_OBJ_FILE).string(),m);
        Trace::drop_surface(m, "surface", {});
        Trace::conclude();
    }
#endif

    return 0;
}