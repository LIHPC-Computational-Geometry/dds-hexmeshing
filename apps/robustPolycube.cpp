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

    cxxopts::Options options(argv[0], "Extract an hexahedral mesh from a labeled tetra mesh with the implementation of \"Robust Quantization for Polycube-Maps\", F. Protais et al. 2022");
    options
        .set_width(80)
        .positional_help("<input> [output] [scaling]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("o,output", "Name of the output folder(s) to create. \%s is replaced by the scaling and \%d by the date and time", cxxopts::value<std::string>()->default_value("robustPolycube_\%s"),"NAME")
            ("s,scaling", "Scaling applied before quantization. Lower is more hexahedra.", cxxopts::value<std::string>()->default_value("1.0"),"VALUE")
            ("v,version", "Print the version (date of last modification) of the underlying executables");
    options.parse_positional({"input","output","scaling"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    path_list.require(ROBUST_POLYCUBE);

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv, { path_list[ROBUST_POLYCUBE] / "rb_generate_deformation", path_list[ROBUST_POLYCUBE] / "rb_generate_quantization" });
    result.require({"input"});
    result.require_not_empty({"output","scaling"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);
    std::string output_folder_name = result["output"];
    bool write_output_collections = !result.is_specified("no-output-collections");

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_3_LABELING,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_robustPolycube_" + global_beginning.filename_string() : //if the input is a collection
                            "robustPolycube"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("robustPolycube",global_beginning.pretty_string(),result["comments"]);

    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%s"), result["scaling"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%d"), global_beginning.filename_string());

    std::string cmd;
    int returncode = 0;
    special_case_policy overwrite_policy = ask;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;
        
        //check if all the input files exist
        if(missing_files_among({
            input_folder.parent_path() / TETRA_MESH_FILE,
            input_folder / PER_TETRA_FACETS_LABELING_FILE
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
            input_folder / output_folder_name / HEX_MESH_FILE,
            input_folder / output_folder_name / INFO_JSON_FILE,
            input_folder / output_folder_name / HEX_MESH_WITH_SJ_GEOGRAM_FILE
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
        txt_logs << "\n|    robustPolycube     |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        //additional output files
        std::string tetra_remesh            = (input_folder / output_folder_name / "tetra_remesh.mesh").string(),
                    tetra_remesh_labeling   = (input_folder / output_folder_name / "tetra_remesh_labeling.txt").string(),
                    polycuboid              = (input_folder / output_folder_name / "polycuboid.mesh").string();//before postprocessing

        cmd = (path_list[ROBUST_POLYCUBE] / "rb_generate_deformation").string() + " " +
              (input_folder.parent_path() / TETRA_MESH_FILE).string() + " " +
              (input_folder / PER_TETRA_FACETS_LABELING_FILE).string() + " " +
              tetra_remesh + " " +
              tetra_remesh_labeling + " " +
              polycuboid +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during rb_generate_deformation call");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        cmd = (path_list[ROBUST_POLYCUBE] / "rb_generate_quantization").string() + " " +
              tetra_remesh + " " +
              tetra_remesh_labeling + " " +
              polycuboid + " " +
              result["scaling"] + " " +
              (input_folder / output_folder_name / HEX_MESH_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();
        returncode = system(cmd.c_str());

        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_comments("error during rb_generate_quantization call");
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder / output_folder_name);

        //compute mesh stats
        HexMeshStats mesh_stats(input_folder / output_folder_name / HEX_MESH_FILE);

        // write info.json
        HexMeshInfo info(input_folder / output_folder_name / INFO_JSON_FILE, HEX_MESH_FILE);
        info.generated_by("robustPolycube");
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
        info.fill_from(mesh_stats);
        info.scale_of("robustPolycube",std::stof(result["scaling"]));

        //write .geogram containing hex mesh + per hex Scaled Jacobian
        mesh_stats.export_as(input_folder / output_folder_name / HEX_MESH_WITH_SJ_GEOGRAM_FILE);

        //TODO write Scaled Jacobian histogram

        //then create a Lua script for Graphite
        GraphiteScript graphite_script(input_folder / output_folder_name / HEX_MESHES_WITH_SJ_LUA_SCRIPT,path_list);
        graphite_script.add_comments("generated by the robustPolycube wrapper of shared-polycube-pipeline");
        graphite_script.add_comments(current_input_beginning.pretty_string());
        graphite_script.hide_text_editor();
        graphite_script.load_object(HEX_MESH_WITH_SJ_GEOGRAM_FILE);
        graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
        graphite_script.set_painting_on_attribute("cells.attr","parula",0.0f,1.0f,true);
        graphite_script.set_lighting(false);
    }

    // in case of a single input folder, open the labeling with Graphite
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        // TODO check if HEX_MESHES_WITH_SJ_LUA_SCRIPT and GRAPHITE_BASH_SCRIPT were successfully created
        cmd = "cd " + (*input_folders.begin() / output_folder_name).string() + " && ./" + GRAPHITE_BASH_SCRIPT + " > /dev/null";//silent output
        system(cmd.c_str());
    }
#endif

    return 0;
}