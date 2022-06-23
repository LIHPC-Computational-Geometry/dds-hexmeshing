#include <iostream>
#include <cxxopts.hpp>

#include "collections.h"

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

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(result["input"].as<std::string>(),input_folders,subcollections)) {
        //an error occured
        return 1;
    }

    std::cout << "Set of input folders (" << input_folders.size() << " elements):" << std::endl;
    for(auto& p : input_folders) {
        std::cout << p.string() << std::endl;
    }

    return 0;
}