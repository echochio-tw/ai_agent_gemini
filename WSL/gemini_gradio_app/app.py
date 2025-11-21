import gradio as gr
import google.generativeai as genai
import os
import subprocess

# --- 1. 配置 Gemini API ---
# 从环境变量中获取 API Key
GEMINI_API_KEY = 'AIzaSyBUSS3XXXXXXXXXXXXXXXXXXXXXXX'

genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 定义工具函数 ---
def execute_shell_command(command: str):
    """
    Executes a shell command in the environment and returns the output.
    """
    try:
        # 使用 shell=True 允许执行 shell 命令
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8' # 确保正确处理命令输出中的字符
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        return_code = result.returncode

        if return_code != 0:
            return (
                f"Command failed with return code {return_code}.\n"
                f"Output: {output}\n"
                f"Error: {error}"
            )
        
        return output if output else "Command executed successfully (no output)."
        
    except Exception as e:
        return f"Error executing command: {str(e)}"

# 初始化 Gemini 模型
model = genai.GenerativeModel(
    'models/gemini-2.5-flash', 
    tools=[execute_shell_command]
)

# --- 3. Gradio 聊天函数 (核心逻辑) ---
def chat_with_gemini(message, history):
    # 初始化聊天会话
    if not hasattr(chat_with_gemini, 'chat_session'):
        chat_with_gemini.chat_session = model.start_chat()

    try:
        # 1. 第一次发送消息给 Gemini
        response = chat_with_gemini.chat_session.send_message(message)

        # 2. 循环处理模型要求的所有工具调用 (使用 response.parts 检查兼容所有SDK版本，包括 0.8.5)
        # 只要响应中包含 function_call part，就继续循环
        while any(part.function_call for part in response.parts):
            
            # 找到第一个 function_call part
            function_call_part = next(
                (part for part in response.parts if part.function_call), None
            )

            if function_call_part is None:
                break

            tool_call = function_call_part.function_call
            tool_name = tool_call.name
            
            # 在 0.8.5 版本中，tool_call.args 是一个映射类型，需要转换为 dict
            tool_args = dict(tool_call.args) 

            if tool_name == "execute_shell_command":
                # 执行工具并获取结果
                tool_output = execute_shell_command(**tool_args)
                
                # 🛠️ 兼容 0.8.5 修复：使用 genai.protos 构造 FunctionResponse Part
                function_response_part = genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": tool_output}
                    )
                )
                
                # 将工具结果发回给 Gemini (第二轮或后续轮次)
                response = chat_with_gemini.chat_session.send_message(
                    function_response_part
                )
            else:
                return f"Error: Unknown tool {tool_name}"

        # 3. 循环结束时，返回最终的文本
        # 如果模型返回了文本，就返回；如果模型只是返回了空响应，Gradio 也能处理空字符串。
        return response.text
        
    except Exception as e:
        return f"Error communicating with Gemini API: {str(e)}"

# --- 4. Gradio 接口配置 (保持兼容性) ---
iface = gr.ChatInterface(
    chat_with_gemini,
    title="🤖 Gemini Chat with Shell Command Tool",
    description=(
        "Ask Gemini questions or input commands like **`做 ls -la /root`** to execute shell commands. "
        "Commands are run in the environment where this script is executed (e.g., WSL/Linux/Windows Shell)."
    )
)

# --- 5. 运行程序 ---
if __name__ == "__main__":
    print("Starting Gradio interface...")
    iface.launch(share=True)
