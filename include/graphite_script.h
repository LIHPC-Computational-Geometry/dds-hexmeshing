#pragma once

#include <iostream>
#include <filesystem>
#include <fstream>
#include <ultimaille/all.h>

#include "paths.h"
#include "parameters.h"

#define BOOL_TO_STRING(value)  ((value) ? "true" : "false")

class GraphiteScript {

public:
    GraphiteScript(std::filesystem::path path, bool append = false) : _lua_script_path(path) {

        _ofs_lua.open(_lua_script_path,append ? std::ios_base::app : std::ios_base::out);//replace if existing
        if(!_ofs_lua.is_open()) {
            std::cerr << "Error : Failed to open " << _lua_script_path.string() << std::endl;
            exit(1);
            // TODO instead of exit(1), raise an exception to manage is_open()==false cases in the main()
            //-> write in the logs that the program was unable to create the scripts, but do not stop the program
        }

        if(append==false) {
            _ofs_lua << "-- Lua" << std::endl;
            //create a bash script that open the Lua script with Graphite:
            //  
            //  #!/bin/bash
            //  cd $(dirname $0) && $GRAPHITE *.lua
            //  
            //TODO write bash script only if GRAPHITE env variable is defined
            std::filesystem::path bash_script_path = path.parent_path() / GRAPHITE_BASH_SCRIPT;
            std::ofstream _ofs_bash;
            _ofs_bash.open(bash_script_path,std::ios_base::out);//replace if existing
            if(_ofs_bash.is_open()) {
                _ofs_bash << "#!/bin/bash" << std::endl;
                _ofs_bash << "cd $(dirname $0) && $GRAPHITE *.lua" << std::endl;
                _ofs_bash.close();
                std::filesystem::permissions(bash_script_path,std::filesystem::perms::owner_exec,std::filesystem::perm_options::add);//add exec permission
            }
            //no exit() if unable to open
        }
        
    }

    ~GraphiteScript() {
        _ofs_lua.close();
    }

    void add_comments(std::string comments) {
        _ofs_lua << "-- " << comments << std::endl;
    }

    void hide_text_editor() {
        _ofs_lua << "text_editor_gui.visible=false" << std::endl;//hide 'Programs' window
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

    void set_vertices_style(bool visible, float red, float green, float blue, int width) {
        _ofs_lua << "scene_graph.current().shader.vertices_style = '" << BOOL_TO_STRING(visible) << "; " << red << " " << green << " " << blue << " 1; " << width << "'" << std::endl;
    }

    void set_painting_on_attribute(std::string attribute_name, std::string colormap, float min, float max, bool reversed) {
        _ofs_lua << "scene_graph.current().shader.painting = 'ATTRIBUTE'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute = '" << attribute_name << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute_min = '" << min << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.attribute_max = '" << max << "'" << std::endl;
        _ofs_lua << "scene_graph.current().shader.colormap = '" << colormap << ";true;0;false;" << BOOL_TO_STRING(reversed) << "'" << std::endl;
    }

private:
    const std::filesystem::path _lua_script_path;
    std::ofstream _ofs_lua;
};

//return true if the labeling was successfully opened, else false
bool fill_labeling(const std::filesystem::path& surface_labeling, UM::FacetAttribute<int>& output_face_attribute) {
    std::ifstream ifs(surface_labeling);
    if(ifs.is_open()) {
        int label, face_number = 0;
        while (ifs >> label) {
            output_face_attribute[face_number] = label;//assume output_face_attribute was initialized with a mesh having the right number of faces
            face_number++;
        }
        ifs.close();
        return true;
    }
    else {
        return false;
    }
}

//true if succeeded, false if error
bool merge_mesh_with_labeling(const std::filesystem::path& surface_mesh_path, const std::filesystem::path& surface_labeling_path, const std::filesystem::path& geogram_filepath) {

    //with Ultimaille, load the surface triangular mesh and the labeling
    UM::Triangles surface_mesh;
    UM::read_by_extension( surface_mesh_path.string() , surface_mesh);

    //create a labeling FacetAttribute and fill it from the labeling file
    UM::FacetAttribute<int> labeling(surface_mesh);
    if(!fill_labeling(surface_labeling_path, labeling)) {
        return false;
        // TODO escalate that PER_SURFACE_TRIANGLE_LABELING_FILE could not be opened, write it in STD_PRINTINGS_FILE
    }

    //write a .geogram file with the surface mesh + labeling as UM::SurfaceAttributes, named "attr"
    //inspired by Trace::drop_facet_scalar()
    UM::write_geogram( geogram_filepath.string() , surface_mesh, UM::SurfaceAttributes{ {}, { { "attr", labeling.ptr } }, {} });
    return true;
}

//both input path must be normalized and trimed
void regenerate_Graphite_visu(const std::filesystem::path& working_data_folder, const std::filesystem::path& folder, DateTimeStr& datetime, const std::string& executable_name) {
    int depth = get_depth_relative(working_data_folder,folder);
    switch(depth) {
        case -1:
            std::cerr << "Error : " << folder.string() << " is not a subfolder of " << working_data_folder.string() << "," << std::endl;
            std::cerr << "the working data folder defined in path.json" << std::endl;
            return;
        case 0:
            std::cerr << "Error: regenerate_Graphite_visu() called on the working data folder." << std::endl;
            std::cerr << "There is no Graphite visualization at this depth." << std::endl;
            return;
        case DEPTH_1_CAD:
            std::cerr << "Error: regenerate_Graphite_visu() called on a CAD model folder." << std::endl;
            std::cerr << "There is no Graphite visualization at this depth." << std::endl;
            return;
        case DEPTH_2_TETRA_MESH: {
            GraphiteScript graphite_script(folder / TETRA_MESH_LUA_SCRIPT);//overwrite mode
            graphite_script.add_comments(std::string("autogenerated by ") + executable_name + " of shared-polycube-pipeline");
            graphite_script.add_comments(datetime.pretty_string());
            graphite_script.hide_text_editor();
            if(std::filesystem::exists(folder / TETRA_MESH_FILE)) {
                graphite_script.load_object(TETRA_MESH_FILE);
                graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
                graphite_script.set_surface_style(false,0.5,0.5,0.5);//hide surface
                graphite_script.set_visible(false);//hide the tetra mesh. else overlaying the surface mesh
            }
            if(std::filesystem::exists(folder / SURFACE_OBJ_FILE)) {
                graphite_script.load_object(SURFACE_OBJ_FILE);
                graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
            }
            } return;
        case DEPTH_3_LABELING: {
            GraphiteScript graphite_script(folder / LABELED_SURFACE_LUA_SCRIPT);//overwrite mode
            graphite_script.add_comments(std::string("autogenerated by ") + executable_name + " of shared-polycube-pipeline");
            graphite_script.add_comments(datetime.pretty_string());
            graphite_script.hide_text_editor();
            if( !std::filesystem::exists(folder / LABELED_SURFACE_GEOGRAM_FILE) && 
                std::filesystem::exists(folder.parent_path() / SURFACE_OBJ_FILE) && 
                std::filesystem::exists(folder / PER_SURFACE_TRIANGLE_LABELING_FILE) ) {
                //the .geogram file doesn't exist, but we have the 2 files needed to generate it
                merge_mesh_with_labeling(folder.parent_path() / SURFACE_OBJ_FILE, folder / PER_SURFACE_TRIANGLE_LABELING_FILE, folder / LABELED_SURFACE_GEOGRAM_FILE);
                // if the labeling has as many labels as the number of faces in the surface mesh, the .geogram file should now exists
            }
            if(std::filesystem::exists(folder / LABELED_SURFACE_GEOGRAM_FILE)) {
                graphite_script.load_object(LABELED_SURFACE_GEOGRAM_FILE);
                graphite_script.set_mesh_style(true,0.0f,0.0f,0.0f,1);
                graphite_script.set_painting_on_attribute("facets.attr","french",0.0f,5.0f,false);
                graphite_script.set_lighting(false);
            }
            if(std::filesystem::exists(folder / TURNING_POINTS_OBJ_FILE)) {
                graphite_script.load_object(TURNING_POINTS_OBJ_FILE);
                graphite_script.set_vertices_style(true,1.0f,1.0f,0.0f,5);
            }
            if( !std::filesystem::exists(folder / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE) && 
                std::filesystem::exists(folder / FAST_SURFACE_POLYCUBE_OBJ_FILE) && 
                std::filesystem::exists(folder / PER_SURFACE_TRIANGLE_LABELING_FILE) ) {
                //the .geogram file doesn't exist, but we have the 2 files needed to generate it
                merge_mesh_with_labeling(folder / FAST_SURFACE_POLYCUBE_OBJ_FILE, folder / PER_SURFACE_TRIANGLE_LABELING_FILE, folder / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE);
                // if the labeling has as many labels as the number of faces in the polycube mesh, the .geogram file should now exists
            }
            if(std::filesystem::exists(folder / LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE)) {
                graphite_script.load_object(LABELED_FAST_SURFACE_POLYCUBE_GEOGRAM_FILE);
                graphite_script.set_mesh_style(true,0.0f,0.0f,0.0f,1);
                graphite_script.set_painting_on_attribute("facets.attr","french",0.0f,5.0f,false);
                graphite_script.set_lighting(false);
            }
            } return;
        case DEPTH_4_HEX_MESH: {
            GraphiteScript graphite_script(folder / HEX_MESHES_WITH_SJ_LUA_SCRIPT);
            graphite_script.add_comments(std::string("autogenerated by ") + executable_name + " of shared-polycube-pipeline");
            graphite_script.add_comments(datetime.pretty_string());
            graphite_script.hide_text_editor();
            if(std::filesystem::exists(folder / HEX_MESH_WITH_SJ_GEOGRAM_FILE)) {
                graphite_script.load_object(HEX_MESH_WITH_SJ_GEOGRAM_FILE);
                graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
                graphite_script.set_painting_on_attribute("cells.attr","parula",0.0f,1.0f,true);//change range to [-1,1] ? (overall range) - Or to [0.5,1] ? (acceptable range)
                graphite_script.set_lighting(false);
            }
            if(std::filesystem::exists(folder / POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE)) {
                if(std::filesystem::exists(folder / HEX_MESH_WITH_SJ_GEOGRAM_FILE)) {
                    graphite_script.set_visible(false);//hide unprocessed hex mesh
                }
                graphite_script.load_object(POSTPROCESSED_HEX_MESH_WITH_SJ_GEOGRAM_FILE);
                graphite_script.set_mesh_style(true,0,0,0,1);//black wireframe
                graphite_script.set_painting_on_attribute("cells.attr","parula",0.0f,1.0f,true);
                graphite_script.set_lighting(false);
            }
            } return;
        default:
            std::cerr << "Error: regenerate_Graphite_visu() called on a folder of invalid depth." << std::endl;
            std::cerr << "There is no Graphite visualization at this depth." << std::endl;
            return;
    }
}