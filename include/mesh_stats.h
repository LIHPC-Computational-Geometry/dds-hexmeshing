#pragma once

#include <string>
#include <filesystem>

#include <ultimaille/all.h>

class TetraMeshStats {

public:
    TetraMeshStats(std::filesystem::path tetra_mesh, std::filesystem::path surface_mesh) {
        UM::read_by_extension(tetra_mesh.string(), tetrahedra);
        UM::read_by_extension(surface_mesh.string(), triangles);

        nb_tetrahedra = tetrahedra.ncells();
        nb_vertices = tetrahedra.nverts();
        nb_surface_triangles = triangles.nfacets();
        nb_surface_vertices = triangles.nverts();
    }

    int get_nb_vertices() const {
        return nb_vertices;
    }

    int get_nb_tetrahedra() const {
        return nb_tetrahedra;
    }

    int get_nb_surface_vertices() const {
        return nb_surface_vertices;
    }

    int get_nb_surface_triangles() const {
        return nb_surface_triangles;
    }

private:
    UM::Tetrahedra tetrahedra;
    UM::Triangles triangles;

    int nb_vertices;
    int nb_tetrahedra;
    int nb_surface_vertices;
    int nb_surface_triangles;

    //maybe also
    // - average edge length
    // - min edge length
    // - max edge length
    // - average mesh size
    // - min mesh size
    // - max mesh size
};