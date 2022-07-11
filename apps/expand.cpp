#include <iostream>
#include <cxxopts.hpp>

#include "collections.h"
#include "cxxopts_ParseResult_custom.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "Expand a collection to its folder list");
    options
        .set_width(80)
        .positional_help("<input>")
        .show_positional_help()
        .add_options()
            ("h,help", "Print help")
            ("i,input", "Path to the input collection", cxxopts::value<std::string>(),"PATH");
    options.parse_positional({"input", "output"});

    //parse results
    cxxopts::ParseResult_custom result(options,argc, argv);
    result.require({"input"});

    PathList path_list;//read paths.json
    path_list.require(WORKING_DATA_FOLDER);

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(result["input"],path_list[WORKING_DATA_FOLDER],input_folders,subcollections)) {
        //an error occured
        return 1;
    }

    std::cout << "Set of input folders (" << input_folders.size() << " elements):" << std::endl;
    for(auto& p : input_folders) {
        std::cout << std::filesystem::relative(p,path_list[WORKING_DATA_FOLDER]).string() << std::endl;
    }

    return 0;
}