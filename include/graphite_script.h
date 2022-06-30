#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>

#include "paths.h"
#include "parameters.h"

#define BOOL_TO_STRING(value)  ((value) ? "true" : "false")

class GraphiteScript {

public:
    GraphiteScript(std::filesystem::path path, const PathList& path_list) : _lua_script_path(path) {

        _ofs_lua.open(_lua_script_path,std::ios_base::out);//replace if existing
        if(!_ofs_lua.is_open()) {
            std::cerr << "Error : Failed to open " << _lua_script_path.string() << std::endl;
            exit(1);
            // TODO instead of exit(1), raise an exception to manage is_open()==false cases in the main()
            //-> write in the logs that the program was unable to create the scripts, but do not stop the program
        }
        _ofs_lua << "-- Lua" << std::endl;

        //create a bash script that open the Lua script with Graphite:
        //  
        //  #!/bin/bash
        //  cd folder && graphite script.lua
        //  
        path_list.require(GRAPHITE,false);
        std::filesystem::path bash_script_path = path.parent_path() / GRAPHITE_BASH_SCRIPT;
        std::ofstream _ofs_bash;
        _ofs_bash.open(bash_script_path,std::ios_base::out);//replace if existing
        if(_ofs_bash.is_open()) {
            _ofs_bash << "#!/bin/bash" << std::endl;
            _ofs_bash << "cd " << _lua_script_path.parent_path().string() << " && " << path_list[GRAPHITE] << " " << _lua_script_path.filename().string() << std::endl;
            _ofs_bash.close();
            std::filesystem::permissions(bash_script_path,std::filesystem::perms::owner_exec,std::filesystem::perm_options::add);//add exec permission
        }
        //no exit() if unable to open
    }

    ~GraphiteScript() {
        _ofs_lua.close();
    }

    void add_comments(std::string comments) {
        _ofs_lua << "-- " << comments << std::endl;
    }

    void load_object(std::string object_path) {
        //object_path is assumed to be the filename of a file in the same folder
        _ofs_lua << "scene_graph.load_object(\"" << object_path << "\")" << std::endl;
    }

    void set_visible(bool visible) {
        _ofs_lua << "scene_graph.current().visible = " << BOOL_TO_STRING(visible) << std::endl;
    }

    void set_lighting(bool lighting) {
        _ofs_lua << "scene_graph.current().shader.lighting = " << BOOL_TO_STRING(lighting) << std::endl;
    }

    void set_mesh_style(bool visible, float red, float green, float blue, int width) {
        _ofs_lua << "scene_graph.current().shader.mesh_style = '" << BOOL_TO_STRING(visible) << "; " << red << " " << green << " " << blue << " 1; " << width << "'" << std::endl;
    }

    void set_surface_style(bool visible, float red, float green, float blue) {
        _ofs_lua << "scene_graph.current().shader.surface_style = '" << BOOL_TO_STRING(visible) << "; " << red << " " << green << " " << blue << " 1'" << std::endl;
    }

    void set_painting_on_attribute(std::string attribute_name, std::string colormap, float min, float max) {
        _ofs_lua << "scene_graph.current().shader.painting = 'ATTRIBUTE'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute = 'facets." << attribute_name << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute_min = '" << min << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute_max = '" << max << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.colormap = '" << colormap << ";true;0;false;false'" << std::endl;
    }

private:
    const std::filesystem::path _lua_script_path;
    std::ofstream _ofs_lua;
};