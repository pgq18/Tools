# Tools
## Install
```bash
git clone https://github.com/pgq18/Tools.git
```
Fill `config.json` with your own config before using.

## Usage
### ASR
#### iFLYTEK
```bash
# pythom 3.8+
pip install --upgrade spark_ai_python
```

```python
from asr.iflytek.iat import record
# Start recording, and it will stop automatically after you stop talking
record()
```

### LLM
Prompt template: [Deepseek prompt library](https://api-docs.deepseek.com/zh-cn/prompt-library)
#### Spark
```bash
pip install cffi gevent greenlet pycparser six websocket websocket-client pyaudio keyboard
```

```python
from models.spark.model import spark_default
# Using default prompt
spark_default("你好")
# Using custom prompt
spark_default(input="你好", prompt="请你扮演一个刚从美国留学回国的人，说话时候会故意中文夹杂部分英文单词，显得非常fancy，对话中总是带有很强的优越感。")
```