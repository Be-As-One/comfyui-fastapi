"""
节点服务主入口
提供统一的节点处理服务接口
"""
from typing import Dict, List, Tuple, Any
from loguru import logger
from .input_node_service import InputNodeService
from .result_node_service import ResultNodeService


class NodeService:
    """节点服务主类"""
    
    def __init__(self):
        self.input_service = InputNodeService()
        self.result_service = ResultNodeService()
    
    def collect_remote_urls(self, wf_json: Dict[str, Any]) -> Tuple[List[str], Dict[str, List[Tuple[str, str, str, Dict[str, Any], Any]]]]:
        """
        收集工作流中所有的远程URL
        
        Args:
            wf_json: 工作流JSON
            
        Returns:
            Tuple[List[str], Dict]: (所有URL列表, URL到节点信息的映射)
        """
        return self.input_service.collect_remote_urls(wf_json)
    
    def update_workflow_paths(self, wf_json: Dict[str, Any], download_results: Dict[str, str], 
                            url_to_node_mapping: Dict[str, List[Tuple[str, str, str, Dict[str, Any], Any]]]) -> None:
        """
        使用下载结果更新工作流中的路径
        
        Args:
            wf_json: 工作流JSON
            download_results: {url: local_path} 的映射
            url_to_node_mapping: URL到节点信息的映射
        """
        self.input_service.update_workflow_paths(wf_json, download_results, url_to_node_mapping)
    
    def collect_workflow_results(self, prompt: Dict[str, Any], outputs: Dict[str, Any], 
                               message_id: str) -> List[Dict[str, Any]]:
        """
        收集工作流的所有结果
        
        Args:
            prompt: 工作流提示数据
            outputs: 执行输出数据
            message_id: 消息ID
            
        Returns:
            List[Dict]: 上传任务列表
        """
        return self.result_service.collect_workflow_results(prompt, outputs, message_id)


# 全局节点服务实例
node_service = NodeService()