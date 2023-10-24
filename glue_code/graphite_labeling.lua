-- Lua (keep this comment, it is an indication for editor's 'run' command)

-- Graphite settings to display a labeled_surface.geogram
-- run with:
-- path/to/graphite labeled_surface.geogram graphite_labeling.lua

text_editor_gui.visible=false
scene_graph.current().shader.mesh_style = 'false; 0 0 0 1; 1'
scene_graph.current().shader.edges_style = 'false; 0 0 0.5 1; 1'
scene_graph.current().shader.border_style = 'false; 0 0 0.5 1; 1'
scene_graph.current().shader.painting = 'ATTRIBUTE'
scene_graph.current().shader.attribute = 'facets.label'
scene_graph.current().shader.attribute_min = '0'
scene_graph.current().shader.attribute_max = '5'
scene_graph.current().shader.colormap = 'french;true;0;false;false'
scene_graph.current().shader.lighting = false
camera.effect = 'SSAO'