#include <iostream>
#include <fstream>
#include <cxxopts.hpp>
#include <regex>
#include <cstdlib>
#include <ultimaille/all.h>
#include <filesystem>

#include "paths.h"
#include "collections.h"
#include "parameters.h"
#include "trace.h"
#include "date_time.h"
#include "cxxopts_ParseResult_custom.h"
#include "graphite_script.h"
#include "info_file.h"
#include "mesh_stats.h"

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
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("o,output", "Name of the output folder(s) to create. \%a is replaced by 'algorithm', \%s by 'size' and \%d by the date and time", cxxopts::value<std::string>()->default_value("\%a_\%s"),"NAME")
            ("s,size", "For 'gmsh', it is a factor in ]0,1]\nFor 'meshgems' and 'netgen', it is the max mesh size", cxxopts::value<std::string>(),"SIZE");
    options.parse_positional({"input", "algorithm", "size", "output"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input", "algorithm", "size"});
    result.require_not_empty({"output"});
    std::filesystem::path input_as_path(result["input"]);
    std::string output_folder_name = result["output"];

    PathList path_list;//read paths.json
    if(result["algorithm"]!="gmsh") {
        path_list.require(SALOME);//except GMSH, the other meshing algorithms use SMESH of SALOME
    }
    path_list.require(GENOMESH);//to extract the surface after

    DateTimeStr global_beginning;//get current time

    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%a"), result["algorithm"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%s"), result["size"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%d"), global_beginning.filename_string());

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,input_folders,subcollections)) {
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_" + result["algorithm"] + "_" + global_beginning.filename_string() : //if the input is a collection
                            "step2mesh"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("step2mesh",global_beginning.pretty_string(),result["comments"]);

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

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|       step2mesh       |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        if(result["algorithm"]=="gmsh") {
            cmd = "../python-scripts/step2mesh_GMSH.py " +
                  (input_folder / STEP_FILE).string() + " " +
                  (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
                  result["size"] +
                  " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        }
        else { //for 'meshgems' or 'netgen', use SALOME
            cmd = "source " + (path_list[SALOME] / "env_launch.sh").string() + " && " +
                  "../python-scripts/step2mesh_SALOME.py " +
                  (input_folder / STEP_FILE).string() + " " +
                  (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
                  result["algorithm"] + " " +
                  result["size"] +
                  " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        }
        returncode = system(cmd.c_str());

        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        //also extract the surface
        cmd = (path_list[GENOMESH] / "build/tris_to_tets").string() + " " +
              (input_folder / output_folder_name / TETRA_MESH_FILE).string() + " " +
              (input_folder / output_folder_name / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name / TRIANGLE_TO_TETRA_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the previous logs)
        returncode = system(cmd.c_str());
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }
        else {
            std::cout << "Done" << std::endl;
            output_collections.success_cases->new_entry(input_folder / output_folder_name);

            // write info.json
            TetraMeshInfo info(input_folder / output_folder_name / INFO_JSON_FILE);
            info.generated_by(result["algorithm"]);
            info.comments(result["comments"]);
            info.date(current_input_beginning.pretty_string());
            TetraMeshStats mesh_stats(input_folder / output_folder_name / TETRA_MESH_FILE,
                                      input_folder / output_folder_name / SURFACE_OBJ_FILE);
            info.vertices(mesh_stats.get_nb_vertices());
            info.tetrahedra(mesh_stats.get_nb_tetrahedra());
            info.surface_vertices(mesh_stats.get_nb_surface_vertices());
            info.surface_triangles(mesh_stats.get_nb_surface_triangles());

            //then create a Lua script for Graphite
            GraphiteScript graphite_script(input_folder / output_folder_name / TETRA_MESH_LUA_SCRIPT,path_list);
            graphite_script.add_comments("generated by step2mesh");
            graphite_script.add_comments(current_input_beginning.pretty_string());
            graphite_script.load_object(TETRA_MESH_FILE);
            graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
            graphite_script.set_surface_style(false,0.5,0.5,0.5);//hide surface
            graphite_script.set_visible(false);//hide the tetra mesh. else overlaying the surface mesh
            graphite_script.load_object(SURFACE_OBJ_FILE);
            graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
        }
    }

    //in case of a single input folder, open the tetra mesh and the surface mesh with Graphite
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        // TODO check if TETRA_MESH_LUA_SCRIPT and GRAPHITE_BASH_SCRIPT were successfully created
        cmd = "cd " + (*input_folders.begin() / output_folder_name).string() + " && ./" + GRAPHITE_BASH_SCRIPT + " > /dev/null";//silent output
        system(cmd.c_str());
    }
#endif

    return 0;
}