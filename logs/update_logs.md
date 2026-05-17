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

修改了F3计算相似度的细节，加上了考虑用户是否为同一种活跃程度的用户的功能
F3的找相似用户的函数还在F4被调用了

# 5.17

修改 F5 受欢迎程度预测功能。

原来的热度预测虽然前端可以输入历史日数，比如 30 天、60 天，但是预测核心只用了最近 7 天计算基础热度、最近 14 天计算趋势，所以 history_days 对预测结果影响不明显，主要只是影响页面展示的历史数据。

本次修改了 hot_predictor.py 中的预测逻辑：

1. 新增 average 函数，用于计算整段历史数据的平均热度。
2. 新增 weighted_average 函数，让越靠近当前日期的数据权重稍高。
3. 新增 calculate_linear_trend 函数，用用户输入的完整 history_days 历史数据做线性趋势分析。
4. 修改 predict_future_heat 函数，不再固定只看最近 7 天或 14 天，而是根据前端传入的 history_days 取整段历史数据进行预测。
5. 修改 recent_average_heat 和趋势判断逻辑，使其基于整段历史数据，而不是只基于最近 7 天。

验证方式：

使用同一个视频 video_id=80，预测未来 7 天，只修改 history_days。

history_days=30 时，future_series 和 history_days=60 时的 future_series 不同，说明前端输入的历史天数已经真正参与预测，原来固定 7 天/14 天的问题已解决。
