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

    cxxopts::Options options(argv[0], "Hexahedral mesh quality improvement with pillowing and smoothing. Provided by the implementation of \"Robust Quantization for Polycube-Maps\", F. Protais et al. 2022");
    options
        .set_width(80)
        .positional_help("<input> [output]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("v,version", "Print the version (date of last modification) of the underlying executables");
    options.parse_positional({"input","output"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(ROBUST_POLYCUBE);

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[ROBUST_POLYCUBE] / "rb_perform_postprocessing" });
    result.require({"input"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);
    bool write_output_collections = !result.is_specified("no-output-collections");

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_4_HEX_MESH,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_postprocess_" + global_beginning.filename_string() : //if the input is a collection
                            "postprocess"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("postprocess",global_beginning.pretty_string(),result["comments"]);

    std::string cmd;
    int returncode = 0;
    special_case_policy overwrite_policy = ask;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;
        
        //check if all the input files exist
        if(missing_files_among({
            input_folder / HEX_MESH_FILE,
            input_folder / "tetra_remesh.mesh"
        },path_list[WORKING_DATA_FOLDER])) {
            returncode = 1;//do not open Graphite in case of single input
            std::cout << "Missing files" << std::endl;
            output_collections.error_cases->new_comments("missing input files");
            output_collections.error_cases->new_entry(input_folder);
            continue;
        }
        
        //check if the output files already exist. if so, ask for confirmation
        bool additional_printing = (overwrite_policy==ask);
        bool need_to_update_lua_script = true;
        if(existing_files_among({
            input_folder / POSTPROCESSED_HEX_MESH_FILE,
            input_folder / POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE
        },path_list[WORKING_DATA_FOLDER],additional_printing)) {
            need_to_update_lua_script = false;//the lua script is assumed to load POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE already
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
        txt_logs << "\n|      postprocess      |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        //TODO need tetra_remesh

        cmd = (path_list[ROBUST_POLYCUBE] / "rb_perform_postprocessing").string() + " " +
              (input_folder / "tetra_remesh.mesh").string() + " " +
              (input_folder / HEX_MESH_FILE).string() + " " +
              (input_folder / POSTPROCESSED_HEX_MESH_FILE).string() +
              " &>> " + (input_folder / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during rb_perform_postprocessing call");
            output_collections.error_cases->new_entry(input_folder);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder);

        //compute mesh stats
        HexMeshStats mesh_stats(input_folder / POSTPROCESSED_HEX_MESH_FILE);

        // write info.json
        HexMeshInfo info(input_folder / INFO_JSON_FILE, POSTPROCESSED_HEX_MESH_FILE);
        info.generated_by("postprocess");
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
        info.fill_from(mesh_stats);
        info.input_of("postprocess",HEX_MESH_FILE);

        //write .geogram containing hex mesh + per hex Scaled Jacobian
        mesh_stats.export_as(input_folder / POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE);

        //TODO write Scaled Jacobian histogram

        if(need_to_update_lua_script) {
            GraphiteScript graphite_script(input_folder / HEX_MESHES_WITH_SJ_LUA_SCRIPT,path_list,true);//append mode
            graphite_script.add_comments("generated by the postprocess wrapper of shared-polycube-pipeline");
            graphite_script.add_comments(current_input_beginning.pretty_string());
            graphite_script.set_visible(false);//hide unprocessed hex mesh
            graphite_script.load_object(POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE);
            graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
            graphite_script.set_painting_on_attribute("cells.attr","parula",0.0f,1.0f,true);
            graphite_script.set_lighting(false);
        }
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