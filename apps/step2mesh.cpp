#include <iostream>
#include <cxxopts.hpp>
#include <regex>
#include <cstdlib>
#include <ultimaille/all.h>

#include "paths.h"
#include "collections.h"
#include "parameters.h"
#include "trace.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Tetrahedral meshing of a .step geometry file");
    options
        .set_width(80)
        .positional_help("<input> <algorithm> <size> [output]")
        .show_positional_help()
        .add_options()
            ("a,algorithm", "Which meshing algorithm to use : 'meshgems', 'netgen' or 'gmsh'", cxxopts::value<std::string>(),"NAME")
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection/folder", cxxopts::value<std::string>(),"PATH")
            ("o,output", "Name of the output folder(s) to create. \%a is replaced by 'algorithm' and \%s by 'size'", cxxopts::value<std::string>()->default_value("\%a_\%s"),"NAME")
            ("s,size", "For 'gmsh', it is a factor in ]0,1]\nFor 'meshgems' and 'netgen', it is the max mesh size", cxxopts::value<std::string>(),"SIZE");
    options.parse_positional({"input", "algorithm", "size", "output"});
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

    if(!result.count("algorithm")) { //if <algorithm> is missing
        std::cerr << "Error : second positional argument <algorithm> is required" << std::endl;
        return 1;
    }

    if(!result.count("size")) { //if <size> is missing
        std::cerr << "Error : third positional argument <size> is required" << std::endl;
        return 1;
    }

    PathList path_list;//read paths.json
    path_list.require(SALOME);//TODO do not require SALOME if GMSH is used

    std::string output_folder_name = result["output"].as<std::string>();
    if(output_folder_name.empty()) {
        std::cerr << "Error : [output] must not be empty" << std::endl;
        return 1;
    }
    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%a"), result["algorithm"].as<std::string>());
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%s"), result["size"].as<std::string>());

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(result["input"].as<std::string>(),input_folders,subcollections)) {
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    std::string cmd;
    for(auto& input_folder : input_folders) {
        std::cout << input_folder.string() << "...";
        //TODO check if the output folder already exist. if so, ask for confirmation
        std::filesystem::create_directory(input_folder / output_folder_name);//create the output folder
        if(result["algorithm"].as<std::string>()=="gmsh") {
            cmd = "../python-scripts/step2mesh_GMSH.py " +
                  (input_folder / "CAD.step").string() + " " +
                  (input_folder / output_folder_name / "tetra.mesh").string() + " " +
                  result["size"].as<std::string>() +
                  " &> " + (input_folder / output_folder_name / "logs.txt").string();//redirect stdout and stderr to file
        }
        else { //for 'meshgems' or 'netgen', use SALOME
            cmd = "source " + (path_list[SALOME] / "env_launch.sh").string() + "\n" +
                  "../python-scripts/step2mesh_SALOME.py " +
                  (input_folder / "CAD.step").string() + " " +
                  (input_folder / output_folder_name / "tetra.mesh").string() + " " +
                  result["algorithm"].as<std::string>() + " " +
                  result["size"].as<std::string>() +
                  " &> " + (input_folder / output_folder_name / "logs.txt").string();//redirect stdout and stderr to file
        }
        std::cout << (system(cmd.c_str()) ? "Error" : "Done") << std::endl;

        // TODO write info.json
    }

    // TODO write output collections

    //in case of a single input folder, open the mesh with Graphite
    //TODO modif (or replace) Trace to put the lua script in the output folder, not in build
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1) {
        path_list.require(GRAPHITE);
        Trace::initialize(path_list[GRAPHITE]);
        UM::Tetrahedra m;
        UM::read_by_extension((*input_folders.begin() / output_folder_name / "tetra.mesh").string(),m);
        Trace::drop_volume(m, "volume", {});
        Trace::conclude();
    }
#endif

    return 0;
}