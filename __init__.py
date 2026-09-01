import bpy
from mathutils import Vector

bl_info = {
    "name": "快速设置灯光",
    "author": "一枫",
    "version": (1, 0, 0),
    "blender": (3, 2, 0),
    "location": "Object Mode > D / 3D View > N 面板 > 快速设置灯光",
    "description": "灯光专用快速设置工具（快捷键 D 弹窗）",
    "category": "Object",
}

# =========================
# 预设常量
# =========================

FOCAL_LENGTH_PRESETS = [12, 18, 24, 35, 50, 85, 135, 200]
FSTOP_PRESETS = [1.2, 1.4, 1.8, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16, 22]
TEMP_PRESETS = [
    ("蜡烛 1.8k", 1850), ("白炽 2.7k", 2700), ("暖白 3.0k", 3000),
    ("卤素 3.2k", 3200), ("荧光 4.2k", 4200), ("日光 5.5k", 5500),
    ("多云 6.5k", 6500), ("阴影 7.5k", 7500), ("晴空 8.5k", 8500),
    ("极蓝 9.5k", 9500), ("蓝天 10k", 10000), ("暮光 12k", 12000),
]

MODULE_TITLE_QUICK_POWER = "快捷调光"
MODULE_TITLE_VIEW_ALIGN = "朝向对齐"
MODULE_TITLE_ROLE_NAME = "灯光命名"
MODULE_TITLE_LINKING = "共享与光照链接"
MODULE_TITLE_COLOR = "色温与光色"
MODULE_TITLE_POWER_EXPOSURE = "强度与曝光"
MODULE_TITLE_TYPE_SHAPE = "类型与光型"
MODULE_TITLE_SIZE_SHADOW = "尺寸与阴影"

MODULE_DISPLAY_ITEMS = (
    "show_quick_power",
    "show_view_align",
    "show_role_name",
    "show_linking",
    "show_color",
    "show_power_exposure",
    "show_type_shape",
    "show_size_shadow",
)

ROW_SCALE_Y = 1.2

MODULE_ICONS = {
    "show_quick_power": "LIGHT_SUN",
    "show_view_align": "ORIENTATION_VIEW",
    "show_role_name": "OUTLINER_OB_LIGHT",
    "show_linking": "LINKED",
    "show_color": "COLOR",
    "show_power_exposure": "LIGHT",
    "show_type_shape": "LIGHT_AREA",
    "show_size_shadow": "SHADING_RENDERED",
}

addon_keymaps = []


# =========================
# 工具函数
# =========================

def get_addon_prefs():
    addon = bpy.context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def get_prefs():
    """返回插件偏好对象"""
    return get_addon_prefs()


def module_is_enabled(context, prop_name):
    """检查模块是否启用"""
    prefs = get_prefs()
    return bool(getattr(prefs, prop_name, True)) if prefs else True


def ui_prop(layout, data, prop, text=None, factor=0.4, toggle=False, icon='NONE'):
    row = layout.row(align=True)
    row.scale_y = ROW_SCALE_Y
    split = row.split(factor=factor, align=True)
    col_label = split.column(align=True)
    col_label.alignment = 'LEFT'
    if text:
        col_label.label(text=text)
    col_prop = split.column(align=True)
    kwargs = {"text": "", "toggle": toggle}
    if icon != 'NONE':
        kwargs["icon"] = icon
    col_prop.prop(data, prop, **kwargs)


def safe_get_light_linking(obj):
    if obj and hasattr(obj, "light_linking"):
        return obj.light_linking
    return None


def light_has_light_linking(obj):
    if not obj or obj.type != 'LIGHT':
        return False
    ll = safe_get_light_linking(obj)
    return bool(ll and (ll.receiver_collection or ll.blocker_collection))


def get_light_linking_share_counts(obj):
    ll = safe_get_light_linking(obj)
    receiver_users = ll.receiver_collection.users if ll and ll.receiver_collection else 0
    blocker_users = ll.blocker_collection.users if ll and ll.blocker_collection else 0
    return receiver_users, blocker_users


def light_has_shared_linking_collections(obj):
    receiver_users, blocker_users = get_light_linking_share_counts(obj)
    return receiver_users > 1 or blocker_users > 1


def light_has_shared_light_data(obj):
    return bool(obj and obj.type == 'LIGHT' and obj.data and obj.data.users > 1)


def light_has_linking_content(obj):
    return light_has_light_linking(obj) or light_has_shared_light_data(obj)


def get_current_view3d_region_data(context):
    if getattr(context, "region_data", None):
        return context.region_data
    space = getattr(context, "space_data", None)
    if space and getattr(space, "type", None) == 'VIEW_3D' and getattr(space, "region_3d", None):
        return space.region_3d
    screen = getattr(context, "screen", None)
    if screen:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D' and sp.region_3d:
                        return sp.region_3d
    return None


# =========================
# 插件偏好（核心修复：模块可见性移到这里）
# =========================

class QUICKLIGHT_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    popup_width: bpy.props.IntProperty(
        name="灯光弹窗宽度",
        default=260,
        min=180,
        max=500,
    )

    # 模块显示设置（全局持久化，不会随场景切换丢失）
    show_quick_power: bpy.props.BoolProperty(
        name=MODULE_TITLE_QUICK_POWER,
        description="显示功率倍数快捷按钮",
        default=True,
    )
    show_view_align: bpy.props.BoolProperty(
        name=MODULE_TITLE_VIEW_ALIGN,
        description="显示灯光朝向当前视图按钮",
        default=True,
    )
    show_role_name: bpy.props.BoolProperty(
        name=MODULE_TITLE_ROLE_NAME,
        description="显示主光、补光、轮廓光、点缀光命名按钮",
        default=True,
    )
    show_linking: bpy.props.BoolProperty(
        name=MODULE_TITLE_LINKING,
        description="显示共享与光照链接模块；当前灯光存在光照链接或共享数据时出现",
        default=True,
    )
    show_color: bpy.props.BoolProperty(
        name=MODULE_TITLE_COLOR,
        description="显示色温预设、色温值与光色设置",
        default=True,
    )
    show_power_exposure: bpy.props.BoolProperty(
        name=MODULE_TITLE_POWER_EXPOSURE,
        description="显示功率/强度与曝光设置",
        default=True,
    )
    show_type_shape: bpy.props.BoolProperty(
        name=MODULE_TITLE_TYPE_SHAPE,
        description="显示灯光类型与面光形状设置",
        default=True,
    )
    show_size_shadow: bpy.props.BoolProperty(
        name=MODULE_TITLE_SIZE_SHADOW,
        description="显示尺寸、半径、角度、柔化等阴影相关设置",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)
        col.label(text="弹窗设置")
        col.prop(self, "popup_width")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="模块显示设置", icon='CHECKBOX_HLT')
        for prop_name in MODULE_DISPLAY_ITEMS:
            col.prop(self, prop_name)
        col.separator(factor=0.35)
        col.label(text="共享与光照链接仅在当前灯光存在光照链接或共享数据时显示。", icon='INFO')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="默认快捷键：D = 快速设置灯光")
        col.label(text="N 面板入口：3D 视图 > N 面板 > 快速设置灯光")


# =========================
# Operators（保持不变）
# =========================

class LIGHT_OT_make_totally_unique(bpy.types.Operator):
    bl_idname = "light.make_totally_unique"
    bl_label = "分离为独立灯光"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'LIGHT':
            return {'CANCELLED'}

        light = obj.data
        if light and light.users > 1:
            obj.data = light.copy()

        ll = safe_get_light_linking(obj)
        if ll:
            for col_attr in ("receiver_collection", "blocker_collection"):
                col = getattr(ll, col_attr)
                if col and col.users > 1:
                    new_col = bpy.data.collections.new(name=f"{col.name}.Unique")
                    for item in col.objects:
                        try:
                            new_col.objects.link(item)
                        except RuntimeError:
                            pass
                    setattr(ll, col_attr, new_col)

        context.view_layer.update()
        self.report({'INFO'}, "已分离为独立灯光数据")
        return {'FINISHED'}


class LIGHT_OT_clear_linking_shared_data(bpy.types.Operator):
    bl_idname = "light.clear_linking_shared_data"
    bl_label = "清除共享"
    bl_description = "仅把共享的光照链接集合复制为当前灯光独立集合，不清除光照链接"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return bool(obj and obj.type == 'LIGHT' and light_has_shared_linking_collections(obj))

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'LIGHT':
            return {'CANCELLED'}

        ll = safe_get_light_linking(obj)
        if not ll:
            return {'CANCELLED'}

        changed = False
        receiver = ll.receiver_collection
        if receiver and receiver.users > 1:
            new_receiver = receiver.copy()
            new_receiver.name = f"{receiver.name}.Unique"
            ll.receiver_collection = new_receiver
            changed = True

        blocker = ll.blocker_collection
        if blocker and blocker.users > 1:
            new_blocker = blocker.copy()
            new_blocker.name = f"{blocker.name}.Unique"
            ll.blocker_collection = new_blocker
            changed = True

        if changed:
            context.view_layer.update()
            self.report({'INFO'}, "已清除光照链接集合共享，链接内容保持不变")
            return {'FINISHED'}

        self.report({'INFO'}, "当前光照链接没有共享集合")
        return {'CANCELLED'}


class LIGHT_OT_reset_linking(bpy.types.Operator):
    bl_idname = "light.reset_linking"
    bl_label = "重置链接"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT' and hasattr(context.object, "light_linking")

    def execute(self, context):
        obj = context.object
        ll = safe_get_light_linking(obj)
        if ll:
            ll.receiver_collection = None
            ll.blocker_collection = None
            self.report({'INFO'}, "已清除光照链接")
        else:
            self.report({'WARNING'}, "当前灯光没有光照链接数据")
            return {'CANCELLED'}
        return {'FINISHED'}


class LIGHT_OT_set_temp_preset(bpy.types.Operator):
    bl_idname = "light.set_temp_preset"
    bl_label = "设置色温"
    bl_options = {'UNDO'}

    kelvin: bpy.props.FloatProperty(default=6500.0)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def execute(self, context):
        obj = context.object
        light = obj.data
        if not hasattr(light, "use_temperature"):
            self.report({'WARNING'}, "当前灯光类型不支持色温设置")
            return {'CANCELLED'}
        light.use_temperature = True
        light.temperature = self.kelvin
        self.report({'INFO'}, f"已设置色温为 {int(self.kelvin)} K")
        return {'FINISHED'}


class LIGHT_OT_multiply_power(bpy.types.Operator):
    bl_idname = "light.multiply_power"
    bl_label = "调整功率倍数"
    bl_options = {'REGISTER', 'UNDO'}

    factor: bpy.props.FloatProperty(default=1.0)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def execute(self, context):
        context.object.data.energy *= self.factor
        self.report({'INFO'}, f"功率已调整为 {context.object.data.energy:.3f}")
        return {'FINISHED'}


class LIGHT_OT_align_to_view_direction(bpy.types.Operator):
    bl_idname = "light.align_to_view_direction"
    bl_label = "灯光朝向当前视图"
    bl_description = "让灯光沿当前 3D 视图的观察方向照射；例如前视图会从前往后打光"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def execute(self, context):
        obj = context.object
        r3d = get_current_view3d_region_data(context)
        if not r3d:
            self.report({'WARNING'}, "未找到当前 3D 视图")
            return {'CANCELLED'}

        view_dir = r3d.view_rotation @ Vector((0.0, 0.0, -1.0))
        if view_dir.length == 0:
            self.report({'WARNING'}, "无法读取当前视图方向")
            return {'CANCELLED'}

        obj.rotation_euler = view_dir.to_track_quat('-Z', 'Y').to_euler()
        context.view_layer.update()
        self.report({'INFO'}, "灯光已朝向当前视图")
        return {'FINISHED'}


class LIGHT_OT_rename_role(bpy.types.Operator):
    bl_idname = "light.rename_role"
    bl_label = "重命名灯光角色"
    bl_options = {'REGISTER', 'UNDO'}

    role_name: bpy.props.StringProperty(default="主光")

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'LIGHT'

    def execute(self, context):
        obj = context.object
        name = self.role_name.strip()
        if not name:
            return {'CANCELLED'}

        obj.name = name
        if obj.data and obj.data.users <= 1:
            obj.data.name = name

        self.report({'INFO'}, f"已重命名为：{obj.name}")
        return {'FINISHED'}


# =========================
# UI 绘制（保持不变）
# =========================

def draw_module_visibility_controls(layout, context):
    prefs = get_prefs()
    if not prefs:
        return

    box = layout.box()
    col = box.column(align=True)
    col.label(text="模块显示设置", icon='CHECKBOX_HLT')
    for prop_name in MODULE_DISPLAY_ITEMS:
        col.prop(prefs, prop_name)
    col.separator(factor=0.35)
    col.label(text="共享与光照链接仅在当前灯光存在光照链接或共享数据时显示。", icon='INFO')


def draw_module_box(layout, title, icon):
    box = layout.box()
    row = box.row(align=True)
    row.label(text=title, icon=icon)
    return box


def draw_light_ui(layout, context, obj):
    light = obj.data
    ll = safe_get_light_linking(obj)

    # 1. 快捷调光
    if module_is_enabled(context, "show_quick_power"):
        box = draw_module_box(layout, MODULE_TITLE_QUICK_POWER, MODULE_ICONS["show_quick_power"])
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = ROW_SCALE_Y
        for txt, fac in [("骤减", 0.5), ("轻减", 1/1.5), ("轻增", 1.5), ("骤增", 2.0)]:
            row.operator("light.multiply_power", text=txt).factor = fac

    # 2. 类型与光型
    if module_is_enabled(context, "show_type_shape"):
        box = draw_module_box(layout, MODULE_TITLE_TYPE_SHAPE, MODULE_ICONS["show_type_shape"])
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = ROW_SCALE_Y
        row.prop(light, "type", expand=True)
        if light.type == 'AREA':
            row = col.row(align=True)
            row.scale_y = ROW_SCALE_Y
            row.prop(light, "shape", expand=True)

    # 3. 朝向对齐
    if module_is_enabled(context, "show_view_align"):
        box = draw_module_box(layout, MODULE_TITLE_VIEW_ALIGN, MODULE_ICONS["show_view_align"])
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = ROW_SCALE_Y
        row.operator("light.align_to_view_direction", text="灯光朝向当前视图")

    # 4. 角色命名
    if module_is_enabled(context, "show_role_name"):
        box = draw_module_box(layout, MODULE_TITLE_ROLE_NAME, MODULE_ICONS["show_role_name"])
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = ROW_SCALE_Y
        for role in ["主光", "补光", "轮廓光", "点缀光"]:
            op = row.operator("light.rename_role", text=role)
            op.role_name = role

    # 5. 共享与光照链接
    if module_is_enabled(context, "show_linking") and light_has_linking_content(obj):
        box = draw_module_box(layout, MODULE_TITLE_LINKING, MODULE_ICONS["show_linking"])
        col = box.column(align=True)
        receiver_col = ll.receiver_collection if ll and ll.receiver_collection else None
        blocker_col = ll.blocker_collection if ll and ll.blocker_collection else None
        has_light_linking = bool(receiver_col or blocker_col)
        receiver_users, blocker_users = get_light_linking_share_counts(obj)
        has_shared_linking = receiver_users > 1 or blocker_users > 1
        data_users = light.users if light else 0

        if has_light_linking:
            col.label(text="光照链接：已设置", icon='LINKED')
            if has_shared_linking:
                shared_parts = []
                if receiver_users > 1:
                    shared_parts.append(f"接收 {receiver_users}")
                if blocker_users > 1:
                    shared_parts.append(f"阻挡 {blocker_users}")
                col.label(text="共享数量：" + " / ".join(shared_parts), icon='DUPLICATE')
                row = col.row(align=True)
                row.scale_y = ROW_SCALE_Y
                row.alert = True
                row.operator("light.clear_linking_shared_data", text="清除共享", icon='RESTRICT_INSTANCED_ON')
            row = col.row(align=True)
            row.scale_y = ROW_SCALE_Y
            row.operator("light.reset_linking", text="清除光照链接", icon='TRASH')
        elif data_users > 1:
            col.label(text=f"灯光数据被共享：{data_users}", icon='DUPLICATE')
            row = col.row(align=True)
            row.scale_y = ROW_SCALE_Y
            row.alert = True
            row.operator("light.make_totally_unique", text="独立化当前灯光数据", icon='UNLINKED')

    # 6. 色温与光色
    if module_is_enabled(context, "show_color"):
        box = draw_module_box(layout, MODULE_TITLE_COLOR, MODULE_ICONS["show_color"])
        col = box.column(align=True)
        if hasattr(light, "use_temperature"):
            row = col.row(align=True)
            row.scale_y = ROW_SCALE_Y
            row.prop(light, "use_temperature", text="使用色温", toggle=True)
            flow = col.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
            flow.scale_y = ROW_SCALE_Y
            current_kelvin = getattr(light, "temperature", None)
            use_temp = bool(getattr(light, "use_temperature", False))
            for txt, kelvin in TEMP_PRESETS:
                is_active = (
                    use_temp
                    and current_kelvin is not None
                    and abs(float(current_kelvin) - float(kelvin)) <= 1.0
                )
                op = flow.operator("light.set_temp_preset", text=txt, depress=is_active)
                op.kelvin = kelvin
            if light.use_temperature:
                ui_prop(col, light, "temperature", text="色温值", factor=0.4)
            else:
                ui_prop(col, light, "color", text="光色", factor=0.4)
        else:
            ui_prop(col, light, "color", text="颜色", factor=0.4)

    # 7. 强度与曝光
    if module_is_enabled(context, "show_power_exposure"):
        box = draw_module_box(layout, MODULE_TITLE_POWER_EXPOSURE, MODULE_ICONS["show_power_exposure"])
        col = box.column(align=True)
        label = "强度" if light.type == 'SUN' else "功率"
        ui_prop(col, light, "energy", text=label, factor=0.4)
        if hasattr(light, "exposure"):
            ui_prop(col, light, "exposure", text="曝光", factor=0.4)

    # 8. 尺寸与阴影
    if module_is_enabled(context, "show_size_shadow") and light.type in {'AREA', 'SPOT', 'POINT', 'SUN'}:
        box = draw_module_box(layout, MODULE_TITLE_SIZE_SHADOW, MODULE_ICONS["show_size_shadow"])
        col = box.column(align=True)
        if light.type == 'AREA':
            ui_prop(col, light, "size", text="尺寸X", factor=0.4)
            if light.shape in {'RECTANGLE', 'ELLIPSE'}:
                ui_prop(col, light, "size_y", text="尺寸Y", factor=0.4)
            if hasattr(light, "spread"):
                ui_prop(col, light, "spread", text="扩散", factor=0.4)
        elif light.type == 'POINT':
            ui_prop(col, light, "shadow_soft_size", text="半径", factor=0.4)
        elif light.type == 'SPOT':
            ui_prop(col, light, "spot_size", text="角度", factor=0.4)
            ui_prop(col, light, "spot_blend", text="柔化", factor=0.4)
            ui_prop(col, light, "shadow_soft_size", text="半径", factor=0.4)
        elif light.type == 'SUN':
            ui_prop(col, light, "angle", text="角度", factor=0.4)


# =========================
# N 面板
# =========================

class VIEW3D_PT_quick_settings_light(bpy.types.Panel):
    bl_label = "快速设置灯光"
    bl_idname = "VIEW3D_PT_quick_settings_light"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "快速设置灯光"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        draw_module_visibility_controls(layout, context)

        if not obj or obj.type != 'LIGHT':
            box = layout.box()
            box.label(text="请选择一个灯光对象", icon='INFO')
            return

        row = layout.row(align=True)
        row.scale_y = ROW_SCALE_Y
        row.operator(OBJECT_OT_quick_settings_light.bl_idname, text="打开快捷弹窗", icon='WINDOW')

        draw_light_ui(layout, context, obj)


# =========================
# 弹窗 Operator
# =========================

class OBJECT_OT_quick_settings_light(bpy.types.Operator):
    bl_idname = "object.quick_settings_light"
    bl_label = "快速设置灯光"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object and context.active_object.type == 'LIGHT'

    def invoke(self, context, event):
        prefs = get_addon_prefs()
        width = prefs.popup_width if prefs else 220
        return context.window_manager.invoke_popup(self, width=width)

    def draw(self, context):
        draw_light_ui(self.layout, context, context.active_object)

    def execute(self, context):
        return {'FINISHED'}


# =========================
# 注册/注销
# =========================

classes = (
    QUICKLIGHT_AddonPreferences,
    LIGHT_OT_make_totally_unique,
    LIGHT_OT_clear_linking_shared_data,
    LIGHT_OT_reset_linking,
    LIGHT_OT_set_temp_preset,
    LIGHT_OT_multiply_power,
    LIGHT_OT_align_to_view_direction,
    LIGHT_OT_rename_role,
    OBJECT_OT_quick_settings_light,
    VIEW3D_PT_quick_settings_light,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # 已移除 Scene 属性注册
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi_popup = km.keymap_items.new(OBJECT_OT_quick_settings_light.bl_idname, 'D', 'PRESS')
        addon_keymaps.append((km, kmi_popup))


def unregister():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
