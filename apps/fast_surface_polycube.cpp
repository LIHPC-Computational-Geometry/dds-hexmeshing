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
#include "mesh_stats.h"
#include "info_file.h"
#include "user_confirmation.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Generate a surface polycube from a labeled triangle mesh");
    options
        .set_width(80)
        .positional_help("<input>")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("v,version", "Print the version (date of last modification) of the underlying executable");
    options.parse_positional({"input"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(FASTBNDPOLYCUBE);

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[FASTBNDPOLYCUBE] / "fastpolycube" });
    result.require({"input"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_3_LABELING,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    std::string cmd;
    int returncode = 0;
    special_case_policy overwrite_policy = ask;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;
        
        //check if all the input files exist
        if(missing_files_among({
            input_folder.parent_path() / SURFACE_OBJ_FILE,
            input_folder / PER_SURFACE_TRIANGLE_LABELING_FILE
        },path_list[WORKING_DATA_FOLDER])) {
            returncode = 1;//do not open Graphite in case of single input
            std::cout << "Missing files" << std::endl;
            continue;
        }
        
        //check if the output files already exist. if so, ask for confirmation
        bool additional_printing = (overwrite_policy==ask);
        if(existing_files_among({
            input_folder / FAST_SURFACE_POLYCUBE_OBJ_FILE,
            input_folder / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE
        },path_list[WORKING_DATA_FOLDER],additional_printing)) {
            bool user_wants_to_overwrite = ask_for_confirmation("\t-> Are you sure you want to overwrite these files ?",overwrite_policy);
            if(additional_printing) std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;//re-print the input name
            if(user_wants_to_overwrite==false) {
                returncode = 1;//do not open Graphite in case of single input
                std::cout << "Canceled" << std::endl;
                continue;
            }
        }

        std::ofstream txt_logs(input_folder / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n| fast_surface_polycube |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[FASTBNDPOLYCUBE] / "fastpolycube").string() + " " +
              (input_folder.parent_path() / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / FAST_SURFACE_POLYCUBE_OBJ_FILE).string() +
              " &>> " + (input_folder / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            continue;
        }

        std::cout << "Done" << std::endl;

        // TODO compute 
        // - angle distortion
        // - area distortion
        // - stretch
        // and write them into info.json

        //write .geogram containing polycube + labeling

        //with Ultimaille, load the polycube triangular mesh and the labeling
        UM::Triangles surface_polycube;
        UM::read_by_extension( (input_folder / FAST_SURFACE_POLYCUBE_OBJ_FILE).string() , surface_polycube);
        //create a labeling FacetAttribute and fill it
        UM::FacetAttribute<int> labeling(surface_polycube);
        if(fill_labeling(input_folder / PER_SURFACE_TRIANGLE_LABELING_FILE, labeling)) {

            //write a .geogram file with the surface mesh + labeling, named "attr", as UM::SurfaceAttributes
            //inspired by Trace::drop_facet_scalar()
            UM::write_by_extension( (input_folder / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE).string() , surface_polycube, UM::SurfaceAttributes{ {}, { { "attr", labeling.ptr } }, {} });

            //then update the Lua script for Graphite
            GraphiteScript graphite_script(input_folder / LABELED_SURFACE_LUA_SCRIPT, path_list, true);//append mode
            graphite_script.add_comments("generated by fast_surface_polycube of shared-polycube-pipeline");
            graphite_script.add_comments(current_input_beginning.pretty_string());
            graphite_script.load_object(LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE);
            graphite_script.set_mesh_style(true,0.0f,0.0f,0.0f,1);
            graphite_script.set_painting_on_attribute("facets.attr","french",0.0f,5.0f,false);
            graphite_script.set_lighting(false);
        }
        // TODO else, write that the PER_SURFACE_TRIANGLE_LABELING_FILE could not be opened in STD_PRINTINGS_FILE
    }

    // in case of a single input folder, open the labeling with Graphite
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        // TODO check if HEX_MESHES_WITH_SJ_LUA_SCRIPT and GRAPHITE_BASH_SCRIPT were successfully created
        cmd = "cd " + (*input_folders.begin()).string() + " && ./" + GRAPHITE_BASH_SCRIPT + " > /dev/null";//silent output
        system(cmd.c_str());
    }
#endif

    return 0;
}