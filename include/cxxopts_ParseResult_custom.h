#pragma once

#include <iostream>
#include <cxxopts.hpp>
#include <initializer_list>
#include <string>

namespace cxxopts {

class ParseResult_custom {

public:
    ParseResult_custom(cxxopts::Options& options, int argc, char *argv[]) : _options(options) {
        _result = options.parse(argc, argv);

        //manage help printing
        if(_result.count("help")) {
            std::cout << _options.help();
            exit(0);
        }
    }

    void require(std::initializer_list<std::string> required_options) {
        bool missing_options = false;
        for(auto* option = required_options.begin(); option != required_options.end(); ++option) {
            if(!_result.count(*option)) {
                missing_options = true;
                std::cerr << "Error : argument '" << *option << " is required" << std::endl;
            }
        }
        if(missing_options) {
            std::cout << "\n" << _options.help();
            exit(1);
        }
    }

    void require_not_empty(std::initializer_list<std::string> required_not_empty_options) {
        bool empty_options = false;
        for(auto* option = required_not_empty_options.begin(); option != required_not_empty_options.end(); ++option) {
            if(_result[*option].as<std::string>().empty()) {
                empty_options = true;
                std::cerr << "Error : argument '" << *option << " must not be empty" << std::endl;
            }
        }
        if(empty_options) {
            std::cout << "\n" << _options.help();
            exit(1);
        }
    }

    std::string operator[](std::string option) {
        return _result[option].as<std::string>();
    }

private:
    cxxopts::ParseResult _result;
    const cxxopts::Options& _options;//store a reference to cxxopts::Options to call help()
};

}