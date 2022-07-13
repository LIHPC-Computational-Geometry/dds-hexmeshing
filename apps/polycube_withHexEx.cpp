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

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Extract an hexahedral mesh from a labeled tetra mesh with libHexEx");
    options
        .set_width(80)
        .positional_help("<input> [output] [scale]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("n,no-output-collections", "The program will not write output collections for success/error cases")
            ("o,output", "Name of the output folder(s) to create. \%s is replaced by the scale and \%d by the date and time", cxxopts::value<std::string>()->default_value("HexEx_\%s"),"NAME")
            ("s,scale", "Scaling factor applied before libHexEx", cxxopts::value<std::string>()->default_value("1.0"),"VALUE");
    options.parse_positional({"input","output","scale"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input"});
    result.require_not_empty({"output","scale"});
    std::filesystem::path input_as_path = normalized_trimed(result["input"]);
    std::string output_folder_name = result["output"];
    bool write_output_collections = !result.is_specified("no-output-collections");

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);
    // 'polycube_withHexEx' is also in Genomesh, but the one in evocube has a more flexible API
    // the code comes from https://github.com/fprotais/polycube_withHexEx
    path_list.require(EVOCUBE_TWEAKS);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(input_as_path,path_list[WORKING_DATA_FOLDER],DEPTH_3_LABELING,input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //create output collections
    std::string basename = (input_as_path.extension() == ".txt") ? 
                            input_as_path.stem().string() + "_HexEx_" + global_beginning.filename_string() : //if the input is a collection
                            "polycube_withHexEx"; //if the input is a single folder
    OutputCollections output_collections(basename,path_list,result.is_specified("no-output-collections"));
    output_collections.set_header("polycube_withHexEx",global_beginning.pretty_string(),result["comments"]);

    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%s"), result["scale"]);
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%d"), global_beginning.filename_string());

    std::string cmd;
    int returncode = 0;
    for(auto& input_folder : input_folders) {
        std::cout << std::filesystem::relative(input_folder,path_list[WORKING_DATA_FOLDER]).string() << "..." << std::flush;
        //TODO check if the output folder already exist. if so, ask for confirmation

        std::filesystem::create_directory(input_folder / output_folder_name);//create the output folder

        std::ofstream txt_logs(input_folder / output_folder_name / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / output_folder_name / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|  polycube_withHexEx   |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[EVOCUBE_TWEAKS] / "polycube_withHexEx").string() + " " +
              (input_folder.parent_path() / TETRA_MESH_FILE).string() + " " +
              (input_folder / PER_TETRA_FACES_LABELING_FILE).string() + " " +
              (input_folder / output_folder_name / HEX_MESH_FILE).string() + " " +
              result["scale"] +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file
        returncode = system(cmd.c_str());
        
        if(returncode!=0) {
            std::cout << "Error" << std::endl;
            output_collections.error_cases->new_entry(input_folder / output_folder_name);
            continue;
        }

        std::cout << "Done" << std::endl;
        output_collections.success_cases->new_entry(input_folder / output_folder_name);

        // write info.json
        HexMeshInfo info(input_folder / output_folder_name / INFO_JSON_FILE);
        info.generated_by("polycube_withHexEx");
        info.comments(result["comments"]);
        info.date(current_input_beginning.pretty_string());
        HexMeshStats mesh_stats(input_folder / output_folder_name / HEX_MESH_FILE);
        info.vertices(mesh_stats.get_nb_vertices());
        info.hexahedra(mesh_stats.get_nb_hexahedra());
        info.min_SJ(mesh_stats.get_min_SJ());

        //write .geogram containing hex mesh + per hex Scaled Jacobian
        mesh_stats.export_as(input_folder / output_folder_name / HEX_MESH_WITH_SJ_GEOGRAM_FILE);

        //TODO write Scaled Jacobian histogram

        //then create a Lua script for Graphite
        GraphiteScript graphite_script(input_folder / output_folder_name / HEX_MESH_WITH_SJ_LUA_SCRIPT,path_list);
        graphite_script.add_comments("generated by polycube_withHexEx");
        graphite_script.add_comments(current_input_beginning.pretty_string());
        graphite_script.load_object(HEX_MESH_WITH_SJ_GEOGRAM_FILE);
        graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
        graphite_script.set_painting_on_attribute("cells.attr","parula",0.0f,1.0f,true);//change range to [-1,1] ? (overall range) - Or to [0.5,1] ? (acceptable range)
        graphite_script.set_lighting(false);
    }

    // in case of a single input folder, open the labeling with Graphite
#ifdef OPEN_GRAPHITE_AT_THE_END
    if(input_folders.size()==1 && returncode==0) { //TODO if returncode!=0, open the logs
        // TODO check if HEX_MESH_WITH_SJ_LUA_SCRIPT and GRAPHITE_BASH_SCRIPT were successfully created
        cmd = "cd " + (*input_folders.begin() / output_folder_name).string() + " && ./" + GRAPHITE_BASH_SCRIPT + " > /dev/null";//silent output
        system(cmd.c_str());
    }
#endif

    return 0;
}