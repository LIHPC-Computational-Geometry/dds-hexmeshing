#include <iostream>
#include <fstream>
#include <cxxopts.hpp>

#include "collections.h"
#include "paths.h"
#include "parameters.h"
#include "date_time.h"
#include "cxxopts_ParseResult_custom.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Compute a naive labeling based on the per-triangle closest direction");
    options
        .set_width(80)
        .positional_help("<input> [output]")
        .show_positional_help()
        .add_options()
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH")
            ("o,output", "Name of the output folder(s) to create. \%d is replaced by the date and time", cxxopts::value<std::string>()->default_value("naive"),"NAME");
    options.parse_positional({"input","output"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input"});
    result.require_not_empty({"output"});
    std::string output_folder_name = result["output"];

    PathList path_list;//read paths.json
    path_list.require(GENOMESH);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(result["input"],input_folders,subcollections)) {
        //an error occured
        return 1;
    }
    std::cout << "Found " << input_folders.size() << " input folder(s)" << std::endl;

    DateTimeStr global_beginning;//get current time

    //format the output folder name
    output_folder_name = std::regex_replace(output_folder_name, std::regex("\%d"), global_beginning.filename_string());

    std::string cmd;
    for(auto& input_folder : input_folders) {
        std::cout << input_folder.string() << "..." << std::flush;
        //TODO check if the output folder already exist. if so, ask for confirmation

        std::filesystem::create_directory(input_folder / output_folder_name);//create the output folder

        std::ofstream txt_logs(input_folder / output_folder_name / STD_PRINTINGS_FILE,std::ios_base::app);//append mode
        if(!txt_logs.is_open()) {
            std::cerr << "Error : Failed to open " << (input_folder / output_folder_name / STD_PRINTINGS_FILE).string() << std::endl;
            return 1;
        }

        DateTimeStr current_input_beginning;//get current time
        txt_logs << "\n+-----------------------+";
        txt_logs << "\n|    naive_labeling     |";
        txt_logs << "\n|  " << current_input_beginning.pretty_string() << "  |";
        txt_logs << "\n+-----------------------+\n\n";
        txt_logs.close();

        cmd = (path_list[GENOMESH] / "build/naive_labeling").string() + " " +
              (input_folder / TRIANGLE_TO_TETRA_FILE).string() + " " +
              (input_folder / SURFACE_OBJ_FILE).string() + " " +
              (input_folder / output_folder_name / PER_SURFACE_TRIANGLE_LABELING_FILE).string() + " " +
              (input_folder / output_folder_name / PER_TETRA_FACES_LABELING_FILE).string() +
              " &>> " + (input_folder / output_folder_name / STD_PRINTINGS_FILE).string();//redirect stdout and stderr to file (append to the logs of step2mesh)
        std::cout << (system(cmd.c_str()) ? "Error" : "Done") << std::endl;

        // TODO write graphite script
    }

    // TODO write success cases & error cases collections

    // TODO in case of a single input folder, open the labeling with Graphite

    return 0;
}