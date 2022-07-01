#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>

#include "paths.h"

class InfoFile {

public:
    InfoFile(std::filesystem::path path) : _path(path) {

    }

    ~InfoFile() {
        std::ofstream ofs(_path);
        if(ofs.is_open()) {
            ofs << std::setw(4) << _json << std::endl;
            ofs.close();
        }
        else {
            std::cerr << "Error : unable to write " << _path.string() << std::endl;
        }
    }

    void add_entry(std::string key, std::string value) {
        _json[key] = value;
    }

    void add_entry(std::string key, int value) {
        _json[key] = value;
    }

    void add_entry(std::string key, std::string subkey, std::string value) {
        _json[key][subkey] = value;
    }

    void add_entry(std::string key, std::string subkey, int value) {
        _json[key][subkey] = value;
    }

    void generated_by(std::string value) {
        _json["generated_by"] = value;
    }

    void comments(std::string value) {
        _json["comments"] = value;
    }

    void date(std::string value) {
        _json["date"] = value;
    }

private:
    std::filesystem::path _path;
    nlohmann::json _json;
};



class TetraMeshInfo : public InfoFile {

public:
    TetraMeshInfo(std::filesystem::path path) : InfoFile(path) {}

    void vertices(int value) {
        add_entry("vertices",value);
    }

    void tetrahedra(int value) {
        add_entry("tetrahedra",value);
    }

    void surface_triangles(int value) {
        add_entry("surface_triangles",value);
    }

};



class LabelingInfo : public InfoFile {

public:
    LabelingInfo(std::filesystem::path path) : InfoFile(path) {}
};