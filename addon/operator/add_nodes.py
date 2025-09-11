import bpy
from bpy.types import Operator
import bpy, mathutils
def set_nodes():
    # Generate unique scene name
    base_name = "Scene"
    end_name = base_name
    if bpy.data.scenes.get(end_name) != None:
        i = 1
        end_name = base_name + f".{i:03d}"
        while bpy.data.scenes.get(end_name) != None:
            end_name = base_name + f".{i:03d}"
            i += 1
    
    scene = bpy.context.window.scene.copy()
    
    scene.name = end_name
    scene.use_fake_user = True
    bpy.context.window.scene = scene
    #initialize Scene node group
    def scene_1_node_group():
        scene_1 = scene.node_tree
        #start with a clean node tree
        for node in scene_1.nodes:
            scene_1.nodes.remove(node)
        scene_1.color_tag = 'NONE'
        scene_1.description = ""
        scene_1.default_group_node_width = 140
        
    
        #scene_1 interface
    
        #initialize scene_1 nodes
        #node Exposure
        exposure = scene_1.nodes.new("CompositorNodeExposure")
        exposure.name = "Exposure"
        #Exposure
        exposure.inputs[1].default_value = 0.0
    
        #node Brightness/Contrast
        brightness_contrast = scene_1.nodes.new("CompositorNodeBrightContrast")
        brightness_contrast.name = "Brightness/Contrast"
        #Bright
        brightness_contrast.inputs[1].default_value = 0.0
        #Contrast
        brightness_contrast.inputs[2].default_value = 0.0
    
        #node Color Balance
        color_balance = scene_1.nodes.new("CompositorNodeColorBalance")
        color_balance.name = "Color Balance"
        color_balance.correction_method = 'LIFT_GAMMA_GAIN'
        color_balance.input_whitepoint = mathutils.Color((0.9991403222084045, 1.0003736019134521, 0.998818039894104))
        color_balance.output_whitepoint = mathutils.Color((0.9991403222084045, 1.0003736019134521, 0.998818039894104))
        #Fac
        color_balance.inputs[0].default_value = 1.0
        #Base Lift
        color_balance.inputs[2].default_value = 0.0
        #Color Lift
        color_balance.inputs[3].default_value = (1.0, 1.0, 1.0, 1.0)
        #Base Gamma
        color_balance.inputs[4].default_value = 1.0
        #Color Gamma
        color_balance.inputs[5].default_value = (1.0, 1.0, 1.0, 1.0)
        #Base Gain
        color_balance.inputs[6].default_value = 1.0
        #Color Gain
        color_balance.inputs[7].default_value = (1.0, 1.0, 1.0, 1.0)
    
        #node RGB Curves
        rgb_curves = scene_1.nodes.new("CompositorNodeCurveRGB")
        rgb_curves.name = "RGB Curves"
        #mapping settings
        rgb_curves.mapping.extend = 'EXTRAPOLATED'
        rgb_curves.mapping.tone = 'STANDARD'
        rgb_curves.mapping.black_level = (0.0, 0.0, 0.0)
        rgb_curves.mapping.white_level = (1.0, 1.0, 1.0)
        rgb_curves.mapping.clip_min_x = 0.0
        rgb_curves.mapping.clip_min_y = 0.0
        rgb_curves.mapping.clip_max_x = 1.0
        rgb_curves.mapping.clip_max_y = 1.0
        rgb_curves.mapping.use_clip = True
        #curve 0
        rgb_curves_curve_0 = rgb_curves.mapping.curves[0]
        rgb_curves_curve_0_point_0 = rgb_curves_curve_0.points[0]
        rgb_curves_curve_0_point_0.location = (0.0, 0.0)
        rgb_curves_curve_0_point_0.handle_type = 'AUTO'
        rgb_curves_curve_0_point_1 = rgb_curves_curve_0.points[1]
        rgb_curves_curve_0_point_1.location = (1.0, 1.0)
        rgb_curves_curve_0_point_1.handle_type = 'AUTO'
        #curve 1
        rgb_curves_curve_1 = rgb_curves.mapping.curves[1]
        rgb_curves_curve_1_point_0 = rgb_curves_curve_1.points[0]
        rgb_curves_curve_1_point_0.location = (0.0, 0.0)
        rgb_curves_curve_1_point_0.handle_type = 'AUTO'
        rgb_curves_curve_1_point_1 = rgb_curves_curve_1.points[1]
        rgb_curves_curve_1_point_1.location = (1.0, 1.0)
        rgb_curves_curve_1_point_1.handle_type = 'AUTO'
        #curve 2
        rgb_curves_curve_2 = rgb_curves.mapping.curves[2]
        rgb_curves_curve_2_point_0 = rgb_curves_curve_2.points[0]
        rgb_curves_curve_2_point_0.location = (0.0, 0.0)
        rgb_curves_curve_2_point_0.handle_type = 'AUTO'
        rgb_curves_curve_2_point_1 = rgb_curves_curve_2.points[1]
        rgb_curves_curve_2_point_1.location = (1.0, 1.0)
        rgb_curves_curve_2_point_1.handle_type = 'AUTO'
        #curve 3
        rgb_curves_curve_3 = rgb_curves.mapping.curves[3]
        rgb_curves_curve_3_point_0 = rgb_curves_curve_3.points[0]
        rgb_curves_curve_3_point_0.location = (0.0, 0.0)
        rgb_curves_curve_3_point_0.handle_type = 'AUTO'
        rgb_curves_curve_3_point_1 = rgb_curves_curve_3.points[1]
        rgb_curves_curve_3_point_1.location = (1.0, 1.0)
        rgb_curves_curve_3_point_1.handle_type = 'AUTO'
        #update curve after changes
        rgb_curves.mapping.update()
        #Fac
        rgb_curves.inputs[0].default_value = 1.0
        #Black Level
        rgb_curves.inputs[2].default_value = (0.0, 0.0, 0.0, 1.0)
        #White Level
        rgb_curves.inputs[3].default_value = (1.0, 1.0, 1.0, 1.0)
    
        #node Color Balance.001
        color_balance_001 = scene_1.nodes.new("CompositorNodeColorBalance")
        color_balance_001.name = "Color Balance.001"
        color_balance_001.correction_method = 'LIFT_GAMMA_GAIN'
        color_balance_001.input_whitepoint = mathutils.Color((0.9991403222084045, 1.0003736019134521, 0.998818039894104))
        color_balance_001.output_whitepoint = mathutils.Color((0.9991403222084045, 1.0003736019134521, 0.998818039894104))
        #Fac
        color_balance_001.inputs[0].default_value = 1.0
        #Base Lift
        color_balance_001.inputs[2].default_value = 0.0
        #Color Lift
        color_balance_001.inputs[3].default_value = (1.0, 1.0, 1.0, 1.0)
        #Base Gamma
        color_balance_001.inputs[4].default_value = 1.0
        #Color Gamma
        color_balance_001.inputs[5].default_value = (1.0, 1.0, 1.0, 1.0)
        #Base Gain
        color_balance_001.inputs[6].default_value = 1.0
        #Color Gain
        color_balance_001.inputs[7].default_value = (1.0, 1.0, 1.0, 1.0)
    
        #node HSV(色相/彩度/明度)
        hsv__________ = scene_1.nodes.new("CompositorNodeHueSat")
        hsv__________.name = "HSV(色相/彩度/明度)"
        #Hue
        hsv__________.inputs[1].default_value = 0.5
        #Saturation
        hsv__________.inputs[2].default_value = 1.0
        #Value
        hsv__________.inputs[3].default_value = 1.0
        #Fac
        hsv__________.inputs[4].default_value = 1.0
    
        #node 色相補正
        ____ = scene_1.nodes.new("CompositorNodeHueCorrect")
        ____.name = "色相補正"
        #mapping settings
        ____.mapping.extend = 'EXTRAPOLATED'
        ____.mapping.tone = 'STANDARD'
        ____.mapping.black_level = (0.0, 0.0, 0.0)
        ____.mapping.white_level = (1.0, 1.0, 1.0)
        ____.mapping.clip_min_x = 0.0
        ____.mapping.clip_min_y = 0.0
        ____.mapping.clip_max_x = 1.0
        ____.mapping.clip_max_y = 1.0
        ____.mapping.use_clip = True
        #curve 0
        _____curve_0 = ____.mapping.curves[0]
        for i in range(len(_____curve_0.points.values()) - 1, 1, -1):
            _____curve_0.points.remove(_____curve_0.points[i])
        _____curve_0_point_0 = _____curve_0.points[0]
        _____curve_0_point_0.location = (0.0, 0.5)
        _____curve_0_point_0.handle_type = 'AUTO'
        _____curve_0_point_1 = _____curve_0.points[1]
        _____curve_0_point_1.location = (0.125, 0.5)
        _____curve_0_point_1.handle_type = 'AUTO'
        _____curve_0_point_2 = _____curve_0.points.new(0.25, 0.5)
        _____curve_0_point_2.handle_type = 'AUTO'
        _____curve_0_point_3 = _____curve_0.points.new(0.375, 0.5)
        _____curve_0_point_3.handle_type = 'AUTO'
        _____curve_0_point_4 = _____curve_0.points.new(0.5, 0.5)
        _____curve_0_point_4.handle_type = 'AUTO'
        _____curve_0_point_5 = _____curve_0.points.new(0.625, 0.5)
        _____curve_0_point_5.handle_type = 'AUTO'
        _____curve_0_point_6 = _____curve_0.points.new(0.75, 0.5)
        _____curve_0_point_6.handle_type = 'AUTO'
        _____curve_0_point_7 = _____curve_0.points.new(0.875, 0.5)
        _____curve_0_point_7.handle_type = 'AUTO'
        #curve 1
        _____curve_1 = ____.mapping.curves[1]
        for i in range(len(_____curve_1.points.values()) - 1, 1, -1):
            _____curve_1.points.remove(_____curve_1.points[i])
        _____curve_1_point_0 = _____curve_1.points[0]
        _____curve_1_point_0.location = (0.0, 0.5)
        _____curve_1_point_0.handle_type = 'AUTO'
        _____curve_1_point_1 = _____curve_1.points[1]
        _____curve_1_point_1.location = (0.125, 0.5)
        _____curve_1_point_1.handle_type = 'AUTO'
        _____curve_1_point_2 = _____curve_1.points.new(0.25, 0.5)
        _____curve_1_point_2.handle_type = 'AUTO'
        _____curve_1_point_3 = _____curve_1.points.new(0.375, 0.5)
        _____curve_1_point_3.handle_type = 'AUTO'
        _____curve_1_point_4 = _____curve_1.points.new(0.5, 0.5)
        _____curve_1_point_4.handle_type = 'AUTO'
        _____curve_1_point_5 = _____curve_1.points.new(0.625, 0.5)
        _____curve_1_point_5.handle_type = 'AUTO'
        _____curve_1_point_6 = _____curve_1.points.new(0.75, 0.5)
        _____curve_1_point_6.handle_type = 'AUTO'
        _____curve_1_point_7 = _____curve_1.points.new(0.875, 0.5)
        _____curve_1_point_7.handle_type = 'AUTO'
        #curve 2
        _____curve_2 = ____.mapping.curves[2]
        for i in range(len(_____curve_2.points.values()) - 1, 1, -1):
            _____curve_2.points.remove(_____curve_2.points[i])
        _____curve_2_point_0 = _____curve_2.points[0]
        _____curve_2_point_0.location = (0.0, 0.5)
        _____curve_2_point_0.handle_type = 'AUTO'
        _____curve_2_point_1 = _____curve_2.points[1]
        _____curve_2_point_1.location = (0.125, 0.5)
        _____curve_2_point_1.handle_type = 'AUTO'
        _____curve_2_point_2 = _____curve_2.points.new(0.25, 0.5)
        _____curve_2_point_2.handle_type = 'AUTO'
        _____curve_2_point_3 = _____curve_2.points.new(0.375, 0.5)
        _____curve_2_point_3.handle_type = 'AUTO'
        _____curve_2_point_4 = _____curve_2.points.new(0.5, 0.5)
        _____curve_2_point_4.handle_type = 'AUTO'
        _____curve_2_point_5 = _____curve_2.points.new(0.625, 0.5)
        _____curve_2_point_5.handle_type = 'AUTO'
        _____curve_2_point_6 = _____curve_2.points.new(0.75, 0.5)
        _____curve_2_point_6.handle_type = 'AUTO'
        _____curve_2_point_7 = _____curve_2.points.new(0.875, 0.5)
        _____curve_2_point_7.handle_type = 'AUTO'
        #update curve after changes
        ____.mapping.update()
        #Fac
        ____.inputs[0].default_value = 1.0
    
        #node Composite
        composite = scene_1.nodes.new("CompositorNodeComposite")
        composite.name = "Composite"
    
        #node Viewer
        viewer = scene_1.nodes.new("CompositorNodeViewer")
        viewer.name = "Viewer"
        viewer.ui_shortcut = 0
    
        #node Image
        image = scene_1.nodes.new("CompositorNodeImage")
        image.name = "Image"
        image.frame_duration = 1
        image.frame_offset = 0
        image.frame_start = 1
        image.use_auto_refresh = True
        image.use_cyclic = False
    
    
        #Set locations
        exposure.location = (-35.726806640625, -21.626792907714844)
        brightness_contrast.location = (154.273193359375, -21.626792907714844)
        color_balance.location = (344.273193359375, -21.626792907714844)
        rgb_curves.location = (546.773193359375, -21.626792907714844)
        color_balance_001.location = (796.773193359375, -21.626792907714844)
        hsv__________.location = (986.773193359375, -21.626792907714844)
        ____.location = (1189.273193359375, -21.626792907714844)
        composite.location = (1559.273193359375, 28.373207092285156)
        viewer.location = (1559.273193359375, -71.62679290771484)
        image.location = (-225.726806640625, -21.626792907714844)
    
        #Set dimensions
        exposure.width, exposure.height = 140.0, 100.0
        brightness_contrast.width, brightness_contrast.height = 140.0, 100.0
        color_balance.width, color_balance.height = 140.0, 100.0
        rgb_curves.width, rgb_curves.height = 200.0, 100.0
        color_balance_001.width, color_balance_001.height = 140.0, 100.0
        hsv__________.width, hsv__________.height = 140.0, 100.0
        ____.width, ____.height = 320.0, 100.0
        composite.width, composite.height = 140.0, 100.0
        viewer.width, viewer.height = 140.0, 100.0
        image.width, image.height = 140.0, 100.0
    
        #initialize scene_1 links
        #exposure.Image -> brightness_contrast.Image
        scene_1.links.new(exposure.outputs[0], brightness_contrast.inputs[0])
        #brightness_contrast.Image -> color_balance.Image
        scene_1.links.new(brightness_contrast.outputs[0], color_balance.inputs[1])
        #color_balance.Image -> rgb_curves.Image
        scene_1.links.new(color_balance.outputs[0], rgb_curves.inputs[1])
        #rgb_curves.Image -> color_balance_001.Image
        scene_1.links.new(rgb_curves.outputs[0], color_balance_001.inputs[1])
        #color_balance_001.Image -> hsv__________.Image
        scene_1.links.new(color_balance_001.outputs[0], hsv__________.inputs[0])
        #hsv__________.Image -> ____.Image
        scene_1.links.new(hsv__________.outputs[0], ____.inputs[1])
        #image.Image -> exposure.Image
        scene_1.links.new(image.outputs[0], exposure.inputs[0])
        #____.Image -> composite.Image
        scene_1.links.new(____.outputs[0], composite.inputs[0])
        #____.Image -> viewer.Image
        scene_1.links.new(____.outputs[0], viewer.inputs[0])
        return scene_1
    
    scene_1 = scene_1_node_group()

class RETOUCH_OT_add_nodes(Operator):
    bl_idname = "retouch.add_nodes"
    bl_label = ""
    bl_description = "Add Nodes"

    def execute(self, context):
        if context.scene.use_nodes is False:
            bpy.context.scene.use_nodes = True
        bpy.context.scene.render.compositor_device = 'GPU'
        set_nodes()
        return {"FINISHED"}
classes = (
    RETOUCH_OT_add_nodes,
)