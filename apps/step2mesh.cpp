#include <iostream>
#include <fstream>
#include <cxxopts.hpp>
#include <regex>
#include <cstdlib>
#include <ultimaille/all.h>

#include "paths.h"
#include "collections.h"
#include "parameters.h"
#include "trace.h"
#include "date_time.h"

int main(int argc, char *argv[]) {

    //TODO add an option to skip the surface mesh extraction

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
    if(result["algorithm"].as<std::string>()!="gmsh") {
        path_list.require(SALOME);//except GMSH, the other meshing algorithms use SMESH of SALOME
    }
    path_list.require(GENOMESH);//to extract the surface after

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

    //create the ouput collection files
    //TODO check if the files already exist
    OutputCollection failed_cases("fails",path_list), successed_cases("successes",path_list);
    failed_cases.new_comments("error cases");
    successed_cases.new_comments("success cases");

    std::string cmd;
    int returncode = 0;
    for(auto& input_folder : input_folders) {
        std::cout << input_folder.string() << "..." << std::flush;
        //TODO check if the output folder already exist. if so, ask for confirmation
        std::filesystem::create_directory(input_folder / output_folder_name);//create the output folder

        std::ofstream txt_logs(input_folder / output_folder_name / STD_PRINTINGS_FILE,std::ios_base::out);
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / output_folder_name / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        DateTimeStr date_time_str;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|       step2mesh       |";
        txt_logs << "\n|  " << date_time_str.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        if(result["algorithm"].as<std::string>()=="gmsh") {
            cmd = "../python-scripts/step2mesh_GMSH.py " +
                  (input_folder / STEP_FILE).string() + " " +
                  (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
                  result["size"].as<std::string>() +
                  " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        }
        else { //for 'meshgems' or 'netgen', use SALOME
            cmd = "source " + (path_list[SALOME] / "env_launch.sh").string() + " && " +
                  "../python-scripts/step2mesh_SALOME.py " +
                  (input_folder / STEP_FILE).string() + " " +
                  (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
                  result["algorithm"].as<std::string>() + " " +
                  result["size"].as<std::string>() +
                  " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        }
        returncode = system(cmd.c_str());

        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            failed_cases.new_entry(input_folder / output_folder_name);
            continue;
        }

        // TODO write info.json

        //also extract the surface
        cmd = (path_list[GENOMESH] / "build/tris_to_tets").string() + " " +
              (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
              (input_folder / output_folder_name / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name / TRIANGLE_TO_TETRA_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        returncode = system(cmd.c_str());
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            failed_cases.new_entry(input_folder / output_folder_name);
            continue;
        }
        else {
            std::cout << "Done" << std::endl;
            successed_cases.new_entry(input_folder / output_folder_name);
        }
    }

    //in case of a single input folder, open the tetra mesh and the surface mesh with Graphite
    //TODO modif (or replace) Trace to put the lua script in the output folder, not in build
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        path_list.require(GRAPHITE);
        Trace::initialize(path_list[GRAPHITE]);
        UM::Tetrahedra tetra_mesh;
        UM::read_by_extension((*input_folders.begin() / output_folder_name / TETRA_MESH_FILE).string(),tetra_mesh);
        Trace::drop_volume(tetra_mesh, "volume", {});
        UM::Triangles surface_mesh;
        UM::read_by_extension((*input_folders.begin() / output_folder_name / SURFACE_OBJ_FILE).string(),surface_mesh);
        Trace::drop_surface(surface_mesh, "surface", {});
        Trace::conclude();
    }
#endif

    return 0;
}