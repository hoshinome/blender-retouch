import bpy
from bpy.types import Panel, Context
from ..utils.ui import *


class RetouchPanelMixin:
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BLENDER RETOUCH"

    def draw_prop(self, layout, data, prop, text=""):
        if data is not None:
            layout.prop(data, prop, text=text)


class RETOUCH_PT_main(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_main"
    bl_label = "Blender Retouch"
    bl_order = 0
 
    def draw(self, context):
        layout = self.layout
 
        row = layout.row()
        row.scale_y = 2.0
        row.operator("retouch.add_nodes", text="Load Image", icon="FILE_IMAGE")
 
        layout.prop(context.scene, "retouch_image_only")
 


class RETOUCH_PT_light(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_light"
    bl_label = "Light"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        self.draw_prop(layout, get_node_or_input(context, "Exposure", 1), "default_value", "Exposure")
        self.draw_prop(layout, get_node_or_input(context, "Brightness/Contrast", 2), "default_value", "Contrast")
        self.draw_prop(layout, get_node_or_input(context, "Color Correction", 10), "default_value", "Highlight")
        self.draw_prop(layout, get_node_or_input(context, "Color Correction", 20), "default_value", "Shadow")
        self.draw_prop(layout, get_node_or_input(context, "Color Correction", 9), "default_value", "White Level")
        self.draw_prop(layout, get_node_or_input(context, "Color Correction", 19), "default_value", "Black Level")


class RETOUCH_PT_lift_gamma_gain(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_lift_gamma_gain"
    bl_label = "Lift/Gamma/Gain"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 2
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        self.draw_prop(layout, get_node_or_input(context, "Color Balance", 3), "default_value", "Lift")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance", 5), "default_value", "Gamma")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance", 7), "default_value", "Gain")


class RETOUCH_PT_curves(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_curves"
    bl_label = "RGB Curves"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        if curves_node := get_node_or_input(context, "RGB Curves"):
            layout.template_curve_mapping(curves_node, "mapping", type="COLOR", show_tone=True)


class RETOUCH_PT_color(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color"
    bl_label = "Color"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        self.draw_prop(layout, get_node_or_input(context, "Switch", 0), "default_value", "Monochrome")

        if wb_node := get_node_or_input(context, "Color Balance.001"):
            row = layout.row(align=True)
            row.label(text="White Balance")
            row.operator("ui.eyedropper_color", text="", icon="EYEDROPPER").prop_data_path = (
                get_node_prop_path(context, wb_node, "input_whitepoint")
            )

        self.draw_prop(layout, get_node_or_input(context, "Color Balance.001", 15), "default_value", "Temperature")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance.001", 16), "default_value", "Tint")
        self.draw_prop(layout, get_node_or_input(context, "BR_Color", 1), "default_value", "Saturation")
        self.draw_prop(layout, get_node_or_input(context, "BR_Color", 2), "default_value", "Natural Saturation")


class RETOUCH_PT_hue_correct(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_hue_correct"
    bl_label = "Hue Correct"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        if curves_node := get_node_or_input(context, "Hue Correct"):
            self.layout.template_curve_mapping(curves_node, "mapping", type="HUE")


class RETOUCH_PT_color_balance(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_balance"
    bl_label = "Color Balance"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 6
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        self.draw_prop(layout, get_node_or_input(context, "Color Balance.002", 4), "default_value", "Lift")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance.002", 6), "default_value", "Gamma")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance.002", 8), "default_value", "Gain")
        self.draw_prop(layout, get_node_or_input(context, "Mix", 7), "default_value", "Offset")
        self.draw_prop(layout, get_node_or_input(context, "Color Balance.002", 1), "default_value", "Strength")


class RETOUCH_PT_effect(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_effect"
    bl_label = "Effect"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 7

    def draw(self, context):
        layout = self.layout
        retouch = context.scene.retouch

        row = layout.row(align=True)
        row.prop(retouch, "panel_tabs", expand=True)

        col = layout.column(align=True)
        tabs = retouch.panel_tabs

        if tabs == "Effects":
            self.draw_prop(layout, get_node_or_input(context, "BR_Effect", 1), "default_value", "Texture")
            self.draw_prop(layout, get_node_or_input(context, "BR_Effect", 2), "default_value", "Clarity")
        elif tabs == "Vignette":
            self.draw_prop(col, get_node_or_input(context, "Vignette", 1), "default_value", "Strength")
            self.draw_prop(col, get_node_or_input(context, "Vignette", 2), "default_value", "Feather")
            self.draw_prop(col, get_node_or_input(context, "Vignette", 3), "default_value", "Corner Roundness")
            self.draw_prop(col, get_node_or_input(context, "Vignette", 4), "default_value", "Scale")
        elif tabs == "Grain":
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 1), "default_value")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 2), "default_value", "Strength")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 3), "default_value", "Scale")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 4), "default_value", "Roughness")
            layout.label(text="===Advances===")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 5), "default_value", "Black Level")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 6), "default_value", "Detail")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 7), "default_value", "Shadows")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 8), "default_value", "Midtones")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 9), "default_value", "Highlights")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 10), "default_value", "Sha/Mid")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 11), "default_value", "Mid/High")
            self.draw_prop(layout, get_node_or_input(context, "BR_Grain", 12), "default_value", "Seed")


classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
    RETOUCH_PT_curves,
    RETOUCH_PT_lift_gamma_gain,
    RETOUCH_PT_color,
    RETOUCH_PT_hue_correct,
    RETOUCH_PT_color_balance,
    RETOUCH_PT_effect,
)
