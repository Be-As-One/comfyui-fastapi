#!/usr/bin/env python3
"""
基于 FaceFusion 的视频人脸检测脚本
检测视频中的所有人脸，支持多人脸跟踪和统计
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict
import numpy as np

# 设置 FaceFusion 路径
FACEFUSION_ROOT = os.environ.get('FACEFUSION_ROOT', '/path/to/facefusion')
if os.path.exists(FACEFUSION_ROOT):
    sys.path.insert(0, FACEFUSION_ROOT)

try:
    import facefusion.state_manager as state_manager
    from facefusion.face_analyser import get_many_faces
    from facefusion.vision import read_video_frame, count_video_frame_total, detect_video_fps, detect_video_resolution
    from facefusion.face_helper import calculate_face_distance
    from facefusion.face_store import clear_static_faces
    print("✅ FaceFusion 加载成功")
    FACEFUSION_AVAILABLE = True
except ImportError as e:
    print(f"❌ FaceFusion 不可用: {e}")
    print("请设置: export FACEFUSION_ROOT=/path/to/facefusion")
    FACEFUSION_AVAILABLE = False
    sys.exit(1)


def detect_video_faces(video_path: str,
                       model: str = 'yolo_face',
                       threshold: float = 0.5,
                       mode: str = 'many',
                       sample_interval: int = 1,
                       start_frame: int = 0,
                       end_frame: Optional[int] = None) -> Dict[str, Any]:
    """
    检测视频中的所有人脸
    
    Args:
        video_path: 视频文件路径
        model: 检测模型 (yolo_face, retinaface, scrfd, yunet, many)
        threshold: 检测阈值
        mode: 人脸选择模式 (one, many, reference)
        sample_interval: 采样间隔
        start_frame: 起始帧
        end_frame: 结束帧
    
    Returns:
        检测结果字典
    """
    # 配置 FaceFusion
    state_manager.set_item('face_detector_model', model)
    state_manager.set_item('face_detector_size', '640x640')
    state_manager.set_item('face_detector_score', threshold)
    state_manager.set_item('face_detector_angles', [0])
    state_manager.set_item('face_selector_mode', mode)
    state_manager.set_item('face_landmarker_model', '2dfan4')
    state_manager.set_item('face_recognizer_model', 'arcface_inswapper_128')
    
    # 清空缓存
    clear_static_faces()
    
    # 获取视频信息
    total_frames = count_video_frame_total(video_path)
    fps = detect_video_fps(video_path)
    width, height = detect_video_resolution(video_path)
    
    if end_frame is None:
        end_frame = total_frames
    else:
        end_frame = min(end_frame, total_frames)
    
    print(f"\n📹 视频信息:")
    print(f"  分辨率: {width}x{height}")
    print(f"  帧率: {fps:.2f} FPS")
    print(f"  总帧数: {total_frames}")
    print(f"  检测范围: 帧 {start_frame}-{end_frame}, 间隔 {sample_interval}")
    
    # 检测人脸
    all_faces = []
    frame_faces = defaultdict(list)
    unique_persons = {}
    person_id_counter = 1
    
    print(f"\n🔍 开始检测...")
    for frame_idx in range(start_frame, end_frame, sample_interval):
        # 读取帧
        frame = read_video_frame(video_path, frame_idx)
        if frame is None:
            continue
        
        # 检测人脸
        faces = get_many_faces([frame])
        
        # 处理每个人脸
        for face_idx, face in enumerate(faces):
            # 提取信息
            face_info = {
                'frame': frame_idx,
                'index': face_idx,
                'bbox': face.bbox.tolist() if hasattr(face, 'bbox') else None,
                'score': float(face.score) if hasattr(face, 'score') else 1.0,
                'gender': face.gender if hasattr(face, 'gender') else None,
                'age': int(face.age) if hasattr(face, 'age') and face.age else None,
                'race': face.race if hasattr(face, 'race') else None
            }
            
            # 人脸跟踪（基于 embedding）
            if hasattr(face, 'embedding_norm') and face.embedding_norm is not None:
                person_id = None
                min_distance = float('inf')
                
                # 查找最相似的已知人脸
                for pid, person_data in unique_persons.items():
                    distance = calculate_face_distance(face, person_data['reference_face'])
                    if distance < 0.4 and distance < min_distance:  # 阈值 0.4 (相似度 > 0.6)
                        person_id = pid
                        min_distance = distance
                
                # 如果没找到匹配，创建新人
                if person_id is None:
                    person_id = f"person_{person_id_counter}"
                    person_id_counter += 1
                    unique_persons[person_id] = {
                        'reference_face': face,
                        'first_frame': frame_idx,
                        'last_frame': frame_idx,
                        'appearances': [],
                        'gender': face_info['gender'],
                        'age': face_info['age'],
                        'race': face_info['race']
                    }
                else:
                    # 更新最后出现帧
                    unique_persons[person_id]['last_frame'] = frame_idx
                
                face_info['person_id'] = person_id
                unique_persons[person_id]['appearances'].append(frame_idx)
            
            all_faces.append(face_info)
            frame_faces[frame_idx].append(face_info)
        
        # 进度显示
        if frame_idx % 30 == 0:
            progress = (frame_idx - start_frame) / (end_frame - start_frame) * 100
            print(f"  进度: {progress:.1f}%")
    
    # 统计结果
    result = {
        'video_path': video_path,
        'video_info': {
            'width': width,
            'height': height,
            'fps': fps,
            'total_frames': total_frames
        },
        'detection_settings': {
            'model': model,
            'threshold': threshold,
            'mode': mode,
            'sample_interval': sample_interval,
            'frames_processed': (end_frame - start_frame) // sample_interval
        },
        'statistics': {
            'total_detections': len(all_faces),
            'unique_persons': len(unique_persons),
            'frames_with_faces': len(frame_faces),
            'max_faces_per_frame': max(len(faces) for faces in frame_faces.values()) if frame_faces else 0
        },
        'persons': {},
        'frame_data': {}
    }
    
    # 整理人员信息
    for person_id, person_data in unique_persons.items():
        result['persons'][person_id] = {
            'gender': person_data['gender'],
            'age': person_data['age'],
            'race': person_data['race'],
            'first_frame': person_data['first_frame'],
            'last_frame': person_data['last_frame'],
            'total_appearances': len(person_data['appearances'])
        }
    
    # 整理帧数据（精简版）
    for frame_idx, faces in frame_faces.items():
        result['frame_data'][str(frame_idx)] = {
            'face_count': len(faces),
            'person_ids': [f.get('person_id', f"unknown_{f['index']}") for f in faces]
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(description='检测视频中的人脸')
    parser.add_argument('video', help='视频文件路径')
    parser.add_argument('--model', default='yolo_face', 
                       choices=['yolo_face', 'retinaface', 'scrfd', 'yunet', 'many'],
                       help='检测模型')
    parser.add_argument('--threshold', type=float, default=0.5, help='检测阈值')
    parser.add_argument('--mode', default='many',
                       choices=['one', 'many', 'reference'],
                       help='人脸选择模式')
    parser.add_argument('--interval', type=int, default=5, help='采样间隔')
    parser.add_argument('--start', type=int, default=0, help='起始帧')
    parser.add_argument('--end', type=int, help='结束帧')
    parser.add_argument('--output', help='输出JSON文件')
    
    args = parser.parse_args()
    
    # 执行检测
    result = detect_video_faces(
        args.video,
        model=args.model,
        threshold=args.threshold,
        mode=args.mode,
        sample_interval=args.interval,
        start_frame=args.start,
        end_frame=args.end
    )
    
    # 输出统计
    print(f"\n✅ 检测完成!")
    print(f"\n📊 统计结果:")
    print(f"  总检测数: {result['statistics']['total_detections']}")
    print(f"  唯一人数: {result['statistics']['unique_persons']}")
    print(f"  包含人脸的帧数: {result['statistics']['frames_with_faces']}")
    print(f"  单帧最大人脸数: {result['statistics']['max_faces_per_frame']}")
    
    if result['persons']:
        print(f"\n👥 检测到的人员:")
        for person_id, info in result['persons'].items():
            print(f"  {person_id}:")
            if info['gender']:
                print(f"    性别: {info['gender']}")
            if info['age']:
                print(f"    年龄: {info['age']}")
            print(f"    出现次数: {info['total_appearances']}")
            print(f"    时间范围: 帧 {info['first_frame']}-{info['last_frame']}")
    
    # 保存结果
    if args.output:
        output_file = args.output
    else:
        output_file = Path(args.video).stem + '_faces.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {output_file}")


if __name__ == '__main__':
    main()