Hacker News recently released an official API. Unfortunately, it cannot be used to get the newest posts submitted. This script provides a faux streaming-api like method to indefinitely yield new hacker news submissions.

Can be useful if you want to create cusotm alerts (like email notifications or gtk notifications) with a simple script.

```
pip install lxml ujson requests
```


Works with python 2.7 and python3

Usage
=====


```python
from hn import HNStream

h = HNStream()

for item in h.stream():
    if 'python' in item['title'].lower():
        # trigger a custom alert you've written
        send_email(subject="New python post!", body="<a href='{}'>Link!</a>".format(item['url']))
```
