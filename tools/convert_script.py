import os
import json
import traceback
import sys

def batch_process():
    input_dir, output_dir = get_args()
    if not input_dir or not output_dir: return
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # 遍历输入文件夹
    success_count = 0
    for root, _, files in os.walk(input_dir):
        for file in files:
            # 忽略resx.json结尾与非.json结尾的文件
            if file.endswith('resx.json') or not file.endswith('.json'): continue
            
            input_file_path = os.path.join(root, file)
            output_file_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".txt")
            
            try:
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                compact_data = to_arrays(raw_data)
                
                # 写入文件
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(compact_data, f, ensure_ascii=False, separators=(',', ':'))
                
                print(f"成功: {file}")
                success_count += 1
            except Exception:
                print(f"失败: {file}\n{traceback.format_exc()}")

def get_args():
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print("用法：python convert_script.py <输入路径> <输出路径>")
        return None, None
    
    input_dir = sys.argv[1].strip().strip('"')
    output_dir = sys.argv[2].strip().strip('"')
    return input_dir, output_dir

def to_arrays(raw_data):
    output = []
    last_bg = None 
    last_ch_state = None 
    last_title = None
    
    scenes = raw_data.get("scenes", []) if isinstance(raw_data, dict) else []
    
    for scene in scenes:
        # 此处优先提取章节标题
        # 4: 章节标题 -> [4, "章节标题"]
        title = scene.get("title")
        if title and title != last_title:
            output.append([4, title])
            last_title = title

        # 0: Label -> [0, "label_name"]
        if "label" in scene and scene["label"]:
            output.append([0, scene["label"]])

        blocks = scene.get("texts", [])
        for line in blocks:
            if not isinstance(line, list) or len(line) < 6: continue
            
            who = line[0] or ""
            msg = line[2] or ""
            control = line[5]
            
            current_bg = None
            current_chs = []
            
            if isinstance(control, dict):
                for cmd in control.get("data", []):
                    if not isinstance(cmd, list) or len(cmd) < 3: continue
                    # 背景处理
                    if cmd[1] == "stage":
                        current_bg = cmd[2].get("redraw", {}).get("imageFile", {}).get("file")
                    # 立绘处理
                    elif cmd[1] == "character":
                        d = cmd[2] or {}
                        if d.get("showmode") == 0: continue
                        name = d.get("name")
                        rd = d.get("redraw", {})
                        opts = rd.get("imageFile", {}).get("options", {})
                        if name:
                            # 立绘数组: [姓名, 位置, 表情, 服装]
                            current_chs.append([name, rd.get("posName", "中"), opts.get("face", ""), opts.get("dress", "")])

            # 1: 背景切换 -> [1, "bg_name"]
            if current_bg and current_bg != last_bg:
                output.append([1, current_bg])
                last_bg = current_bg
            
            # 2: 对话 -> [2, "谁", "话", [立绘列表/None]]
            ch_to_save = None
            if current_chs != last_ch_state:
                ch_to_save = current_chs
                last_ch_state = current_chs

            # 只有当有名字、有话或者立绘变了才记录
            if who or msg or ch_to_save is not None:
                dialog = [2, who, msg]
                if ch_to_save is not None:
                    dialog.append(ch_to_save)
                output.append(dialog)

        # 3: 选项 -> [3, [["文字", "跳转"], ["文字", "跳转"]]]
        raw_sels = scene.get("selects", [])
        if raw_sels:
            sel_list = []
            for s in raw_sels:
                if "text" not in s: continue
                
                # 提取 target 或 tag
                target = s.get("target") or s.get("tag") or ""
                
                # 如果不为空且不以 * 开头，则强制补上，有时target与实际节点有偏差
                if target and not target.startswith("*"):
                    target = "*" + target
                
                sel_list.append([
                    s.get("text", ""),
                    target,
                    s.get("exp", "")
                ])
            
            if sel_list:
                output.append([3, sel_list])
        
    return output

if __name__ == "__main__":
    batch_process()