#pragma once

#include <string>
#include <filesystem>
#include <array>
#include <vector>
#include <algorithm>

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

// constexpr int MEDIT__HEX_CORNER_SPLITTING[8][4] = {
//     // /!\ WARNING : MEDIT convention here (.mesh). Different from UM, OVM conventions
//     //      5-------6
//     //     /|      /|
//     //    / |     / |
//     //   1-------2  |
//     //   |  4----|--7
//     //   | /     | /
//     //   |/      |/
//     //   0-------3
// 	{0,3,4,1},//bottom-front-left corner
// 	{3,7,0,2},//bottom-front-right corner
// 	{4,0,7,5},//bottom-back-left corner
// 	{7,4,3,6},//bottom-back-right corner
// 	{1,5,2,0},//top-front-left corner
// 	{2,1,6,3},//top-front-right corner
// 	{5,6,1,4},//top-back-left corner
// 	{6,2,5,7},//top-back-right corner
// };

constexpr int UM__HEX_CORNER_SPLITTING[8][4] = {
    // /!\ WARNING : UltiMaille convention here. Different from Medit, OVM conventions
    //      6-------7
    //     /|      /|
    //    / |     / |
    //   4-------5  |
    //   |  2----|--3
    //   | /     | /
    //   |/      |/
    //   0-------1
	{0,1,2,4},
	{1,3,0,5},
	{2,0,3,6},
	{3,2,1,7},
	{4,6,5,0},
	{5,4,7,1},
	{6,7,4,2},
	{7,5,6,3},
};

class HexMeshStats {

public:
    HexMeshStats(std::filesystem::path path) {
        UM::read_by_extension(path.string(), hexahedra);

        nb_hexahedra = hexahedra.ncells();
        nb_vertices = hexahedra.nverts();

        //compute per-hexahedron Scaled Jacobian

        SJ = new UM::CellAttribute<double>(hexahedra);
        min_SJ = 1.0;
        for (int h : UM::range(hexahedra.ncells())) {
            double per_cell_SJ = 1.0;
            for (int hv : UM::range(8)) {
                std::array<UM::vec3,4> v;
                for (int i : UM::range(4)) v[i] = hexahedra.points[hexahedra.vert(h, UM__HEX_CORNER_SPLITTING[hv][i])];
                UM::vec3 n1 = v[1] - v[0]; n1.normalize();
                UM::vec3 n2 = v[2] - v[0]; n2.normalize();
                UM::vec3 n3 = v[3] - v[0]; n3.normalize();
                per_cell_SJ = std::min(per_cell_SJ, n3 * UM::cross(n1, n2));
            }
            (*SJ)[h] = per_cell_SJ;
            min_SJ = std::min(min_SJ, per_cell_SJ);
        }
    }

    ~HexMeshStats() {
        delete SJ;
    }

    int get_nb_vertices() const {
        return nb_vertices;
    }

    int get_nb_hexahedra() const {
        return nb_hexahedra;
    }

    void get_SJ(std::vector<double>& output) const {
        output.clear();
        for(int cell = 0; cell < nb_hexahedra; cell++) {
            output.push_back((*SJ)[cell]);
        }
    }

    double get_min_SJ() const {
        return min_SJ;
    }

    void export_as(std::filesystem::path path) const {
        //write a .geogram file with the hex mesh + per cell Scaled Jacobian, named "attr"
        UM::write_by_extension(path.string(), hexahedra, UM::VolumeAttributes{ {}, { { "attr", (*SJ).ptr } }, {}, {} });
    }

private:
    UM::Hexahedra hexahedra;
    UM::CellAttribute<double> *SJ;

    int nb_vertices;
    int nb_hexahedra;
    double min_SJ;
};