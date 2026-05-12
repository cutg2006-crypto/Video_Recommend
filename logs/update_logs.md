# 5.11
将视频产生日期设定在现在时间的365内产生这个范围太大了，导致F5热度预测功能失效。所以改用：
将
generate_videos函数中
publish_time = random_time_within_days(365, now)
修改为
publish_time = random_time_within_days(60, now)

将generate_watch_logs函数中
watch_time = random_time_within_days(90, now)
修改为
watch_time = random_time_within_days(45, now)

另外需要修改watch_time和publish_time之间的联动逻辑，使得watch_time<=publish_time

还有一个问题，就是这个热度预测功能有把watch_logs中生成的liked commented shared包括在内吗，如果没有那需要包括在内吗
A：已经包括在内了

另外我看了这个liked commented shared的逻辑，认为(random.random() < 0.05 + finish_rate * 0.35)这样只靠随机数判断有些鲁莽，所以想改用例如：
如果视频是自己喜欢的类别，那就取:
liked = int((random.random(0.5,1)*0.7 +finish_rate*0.3) > 0.5) (这里的所有小数参数都是超参数，只是临时占位，后期也可调)
如果是不感兴趣的，就取：
liked = int((random.random()*0.7 +finish_rate*0.3) > 0.5)
shared ,commented也是同理

然后对于这个finish_rate我觉得也可以分成爱看和不爱看的分类讨论？
比如爱看的finish_rate=random.random(0.5,1)
不爱看的finish_rate=random.random(0,1)

## ok，都改好了，顺便把用户数调到了50k，将每种用户群体的每日观看数也往上面调了，现在热度预测可以了

# 5.12

今天准备改F3相似度和F4视频推荐部分