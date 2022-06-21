#include <iostream>
#include <cxxopts.hpp>

#include "paths.h"
#include "collections.h"

int main(int argc, char *argv[]) {

    cxxopts::Options options(argv[0], "A wrapper for some hex-mesh generation tools to use the same data folder");
    options
        .set_width(80)
        .positional_help("<input> [output]")
        .show_positional_help()
        .add_options()
            ("c,comments", "Comments about the aim of this execution", cxxopts::value<std::string>()->default_value(""),"TEXT")
            ("h,help", "Print help")
            ("i,input", "Path to the input collection/folder", cxxopts::value<std::string>(),"PATH")
            ("o,output", "Name of the output folder(s) to create", cxxopts::value<std::string>()->default_value("test"),"TEXT");
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

    std::cout << "input is " << result["input"].as<std::string>() << std::endl;
    std::cout << "output is " << result["output"].as<std::string>() << std::endl;
    std::cout << "comments is " << result["comments"].as<std::string>() << std::endl;

    paths p;//read paths.json
    std::cout << "shared_data = " << p.shared_data() << std::endl;

    std::set<std::filesystem::path> input_folders, subcollections;
    if(expand_collection(p.shared_data() / result["input"].as<std::string>(),input_folders,subcollections)) {
        //an error occured
        return 1;
    }

    std::cout << "Set of input folders (" << input_folders.size() << " elements):" << std::endl;
    for(auto& p : input_folders) {
        std::cout << p.string() << std::endl;
    }

    return 0;
}