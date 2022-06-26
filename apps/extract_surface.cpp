#include <iostream>
#include <fstream>
#include <cxxopts.hpp>

#include "collections.h"
#include "paths.h"
#include "trace.h"
#include "parameters.h"
#include "date_time.h"

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
    cxxopts::ParseResult result = options.parse(argc, argv);

    if(result.count("help"))
    {
        std::cout << options.help() << std::endl;
        return 0;
    }

    if(!result.count("input")) { //if <input> is missing
        std::cerr << "Error : first positional argument <input> is required" << std::endl;
        return 1;
    }

    PathList path_list;//read paths.json
    path_list.require(GENOMESH);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(result["input"].as<std::string>(),input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    std::string cmd;
    for(auto& input_folder : input_folders) {
        std::cout << input_folder.string() << "..." << std::flush;
        //TODO check if the output files already exist

        std::ofstream txt_logs(input_folder / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        //add a separator between the existing printings of step2mesh and the ones of extract_surface

        DateTimeStr date_time_str;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|    extract_surface    |";
        txt_logs << "\n|  " << date_time_str.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[GENOMESH] / "build/tris_to_tets").string() + " " +
              (input_folder / TETRA_MESH_FILE).string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / TRIANGLE_TO_TETRA_FILE).string() +
              " &>> " + (input_folder / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the logs of step2mesh)
        std::cout << (system(cmd.c_str()) ? "Error" : "Done") << std::endl;
    }

    // TODO write a collections with failed cases

    //in case of a single input folder, open the surface mesh with Graphite
    //TODO modif (or replace) Trace to put the lua script in the output folder, not in build
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1) {
        path_list.require(GRAPHITE);
        Trace::initialize(path_list[GRAPHITE]);
        UM::Triangles m;
        UM::read_by_extension((*input_folders.begin() / SURFACE_OBJ_FILE).string(),m);
        Trace::drop_surface(m, "surface", {});
        Trace::conclude();
    }
#endif

    return 0;
}