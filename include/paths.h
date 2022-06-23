#pragma once

#include <stdlib.h>
#include <iostream>
#include <filesystem>
#include <fstream>
#include <string>
#include <map>
#include <nlohmann/json.hpp>

#include "parameters.h"

std::filesystem::path to_canonical_path(std::string path_as_str) {
    if(path_as_str.size()>=1 && path_as_str[0]=='~') {
        //replace "~" with the value of $HOME
        path_as_str = getenv("HOME") + path_as_str.substr(1);
    }
    return std::filesystem::weakly_canonical(path_as_str);//do not check if the path exist
};

//if 'entry_name' is an entry of 'json' and is not empty, add it to 'string2path'
inline void try_to_insert(const nlohmann::json& json, std::map<std::string,std::filesystem::path>& string2path, std::string entry_name) {
    try {
        std::filesystem::path tmp_path = to_canonical_path(json.at( nlohmann::json::json_pointer("/"+entry_name) ));
        if(!tmp_path.empty()) {
            string2path[entry_name] = tmp_path;
        }
    }
    catch (nlohmann::json::out_of_range) { /* if 'entry_name' does not exist in 'json', no entry added in 'string2path' */ }
};

class PathList {

public:
    PathList() {
        std::ifstream i("../paths.json");
        if (i.good()) {
            i >> _j;
            try_to_insert(_j,_string2path,SALOME);
        }
        else
            std::cerr << "Error : paths.json doesn't exist" << std::endl;
        i.close();
    };

    void dump() {
        for(auto it = _string2path.begin(); it != _string2path.end(); ++it) {
            std::cout << "_string2path[\"" << it->first << "\"]=" << it->second << std::endl;
        }
    }

    std::filesystem::path operator[](std::string entry) const {
        return _string2path.at(entry);
    }

    void require(std::string entry) const {
        try {
            _string2path.at(entry);
        }
        catch (std::out_of_range) {
            std::cerr << "Error : '" << entry << "' is required in paths.json" << std::endl;
            exit(1);
        }
        return;
    }

private:
    nlohmann::json _j;
    std::map<std::string,std::filesystem::path> _string2path;
};