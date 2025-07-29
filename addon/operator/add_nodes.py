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
        #node Composite
        composite = scene_1.nodes.new("CompositorNodeComposite")
        composite.name = "Composite"
        composite.use_alpha = True
        #Alpha
        composite.inputs[1].default_value = 1.0
    
        #node Render Layers
        render_layers = scene_1.nodes.new("CompositorNodeRLayers")
        render_layers.name = "Render Layers"
        render_layers.layer = 'ViewLayer'
    
        #node カラーバランス
        _______ = scene_1.nodes.new("CompositorNodeColorBalance")
        _______.name = "カラーバランス"
        _______.correction_method = 'LIFT_GAMMA_GAIN'
        _______.gain = mathutils.Color((1.0, 1.0, 1.0))
        _______.gamma = mathutils.Color((1.0, 1.0, 1.0))
        _______.lift = mathutils.Color((1.0, 1.0, 1.0))
        #Fac
        _______.inputs[0].default_value = 1.0
    
        #node 輝度/コントラスト
        _________ = scene_1.nodes.new("CompositorNodeBrightContrast")
        _________.name = "輝度/コントラスト"
        _________.use_premultiply = True
        #Bright
        _________.inputs[1].default_value = 0.0
        #Contrast
        _________.inputs[2].default_value = 1.0
    
        #node 露出
        __ = scene_1.nodes.new("CompositorNodeExposure")
        __.name = "露出"
        #Exposure
        __.inputs[1].default_value = 1.0
    
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
    
        #node RGBカーブ
        rgb___ = scene_1.nodes.new("CompositorNodeCurveRGB")
        rgb___.name = "RGBカーブ"
        #mapping settings
        rgb___.mapping.extend = 'EXTRAPOLATED'
        rgb___.mapping.tone = 'STANDARD'
        rgb___.mapping.black_level = (0.0, 0.0, 0.0)
        rgb___.mapping.white_level = (1.0, 1.0, 1.0)
        rgb___.mapping.clip_min_x = 0.0
        rgb___.mapping.clip_min_y = 0.0
        rgb___.mapping.clip_max_x = 1.0
        rgb___.mapping.clip_max_y = 1.0
        rgb___.mapping.use_clip = True
        #curve 0
        rgb____curve_0 = rgb___.mapping.curves[0]
        rgb____curve_0_point_0 = rgb____curve_0.points[0]
        rgb____curve_0_point_0.location = (0.0, 0.0)
        rgb____curve_0_point_0.handle_type = 'AUTO'
        rgb____curve_0_point_1 = rgb____curve_0.points[1]
        rgb____curve_0_point_1.location = (1.0, 1.0)
        rgb____curve_0_point_1.handle_type = 'AUTO'
        #curve 1
        rgb____curve_1 = rgb___.mapping.curves[1]
        rgb____curve_1_point_0 = rgb____curve_1.points[0]
        rgb____curve_1_point_0.location = (0.0, 0.0)
        rgb____curve_1_point_0.handle_type = 'AUTO'
        rgb____curve_1_point_1 = rgb____curve_1.points[1]
        rgb____curve_1_point_1.location = (1.0, 1.0)
        rgb____curve_1_point_1.handle_type = 'AUTO'
        #curve 2
        rgb____curve_2 = rgb___.mapping.curves[2]
        rgb____curve_2_point_0 = rgb____curve_2.points[0]
        rgb____curve_2_point_0.location = (0.0, 0.0)
        rgb____curve_2_point_0.handle_type = 'AUTO'
        rgb____curve_2_point_1 = rgb____curve_2.points[1]
        rgb____curve_2_point_1.location = (1.0, 1.0)
        rgb____curve_2_point_1.handle_type = 'AUTO'
        #curve 3
        rgb____curve_3 = rgb___.mapping.curves[3]
        rgb____curve_3_point_0 = rgb____curve_3.points[0]
        rgb____curve_3_point_0.location = (0.0, 0.0)
        rgb____curve_3_point_0.handle_type = 'AUTO'
        rgb____curve_3_point_1 = rgb____curve_3.points[1]
        rgb____curve_3_point_1.location = (1.0, 1.0)
        rgb____curve_3_point_1.handle_type = 'AUTO'
        #update curve after changes
        rgb___.mapping.update()
        #Fac
        rgb___.inputs[0].default_value = 1.0
        #Black Level
        rgb___.inputs[2].default_value = (0.0, 0.0, 0.0, 1.0)
        #White Level
        rgb___.inputs[3].default_value = (1.0, 1.0, 1.0, 1.0)
    
        #node 画像
        ___1 = scene_1.nodes.new("CompositorNodeImage")
        ___1.name = "画像"
        ___1.frame_duration = 1
        ___1.frame_offset = 0
        ___1.frame_start = 1
        ___1.use_auto_refresh = True
        ___1.use_cyclic = False
        ___1.use_straight_alpha_output = False
    
        #node ビューアー
        _____ = scene_1.nodes.new("CompositorNodeViewer")
        _____.name = "ビューアー"
        _____.use_alpha = True
        #Alpha
        _____.inputs[1].default_value = 1.0
    
        #node カラーバランス.001
        ________001 = scene_1.nodes.new("CompositorNodeColorBalance")
        ________001.name = "カラーバランス.001"
        ________001.correction_method = 'LIFT_GAMMA_GAIN'
        ________001.gain = mathutils.Color((1.0, 1.0, 1.0))
        ________001.gamma = mathutils.Color((1.0, 1.0, 1.0))
        ________001.lift = mathutils.Color((1.0, 1.0, 1.0))
        #Fac
        ________001.inputs[0].default_value = 1.0
    
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
    
    
        #Set locations
        composite.location = (1829.191162109375, 84.1082763671875)
        render_layers.location = (-530.3876953125, 194.8547821044922)
        _______.location = (1355.857177734375, 58.945648193359375)
        _________.location = (-193.49203491210938, 12.901390075683594)
        __.location = (-411.3983459472656, -7.522392272949219)
        ____.location = (1041.4686279296875, -166.97079467773438)
        rgb___.location = (579.1456298828125, 3.0018463134765625)
        ___1.location = (-647.6041870117188, 18.832401275634766)
        _____.location = (1871.4755859375, 205.16592407226562)
        ________001.location = (101.74832916259766, -19.633712768554688)
        hsv__________.location = (859.7230224609375, -196.1482391357422)
    
        #Set dimensions
        composite.width, composite.height = 140.0, 100.0
        render_layers.width, render_layers.height = 240.0, 100.0
        _______.width, _______.height = 400.0, 100.0
        _________.width, _________.height = 140.0, 100.0
        __.width, __.height = 140.0, 100.0
        ____.width, ____.height = 320.0, 100.0
        rgb___.width, rgb___.height = 200.0, 100.0
        ___1.width, ___1.height = 140.0, 100.0
        _____.width, _____.height = 140.0, 100.0
        ________001.width, ________001.height = 400.0, 100.0
        hsv__________.width, hsv__________.height = 140.0, 100.0
    
        #initialize scene_1 links
        #__.Image -> _________.Image
        scene_1.links.new(__.outputs[0], _________.inputs[0])
        #___1.Image -> __.Image
        scene_1.links.new(___1.outputs[0], __.inputs[0])
        #_______.Image -> composite.Image
        scene_1.links.new(_______.outputs[0], composite.inputs[0])
        #_______.Image -> _____.Image
        scene_1.links.new(_______.outputs[0], _____.inputs[0])
        #________001.Image -> rgb___.Image
        scene_1.links.new(________001.outputs[0], rgb___.inputs[1])
        #_________.Image -> ________001.Image
        scene_1.links.new(_________.outputs[0], ________001.inputs[1])
        #hsv__________.Image -> ____.Image
        scene_1.links.new(hsv__________.outputs[0], ____.inputs[1])
        #rgb___.Image -> hsv__________.Image
        scene_1.links.new(rgb___.outputs[0], hsv__________.inputs[0])
        #____.Image -> _______.Image
        scene_1.links.new(____.outputs[0], _______.inputs[1])
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