Hacker News recently released an official API. Unfortunately, it cannot be used to get the newest posts submitted. This script provides a faux streaming-api like method to indefinitely yield new hacker news submissions.

Can be useful if you want to create cusotm alerts (like email notifications or gtk notifications) with a simple script.

```
pip install lxml ujson
```

Usage
=====


```python
from hn import HNStream

h = HNStream()

for item in h.stream():
    #do something interesting, like:
    if 'python' in item.title.lower():
        send_email(subject="New python post!")
```
