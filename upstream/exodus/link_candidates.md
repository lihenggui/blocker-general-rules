# Exodus link candidates

Only reciprocal, unique matches with an exact keyword after stripping trailing dots are linked automatically.
Prefix-only, multiple-tracker, and multiple-local-rule matches need human review. App ids are never Exodus ids.

## Ambiguous matches

| App id | Local rule | Exodus candidates and keyword evidence |
| --- | --- | --- |
| 4 | Sensors Data | 248 Sensors Analytics: com.sensorsdata.analytics. ↔ com.sensorsdata.analytics.android.sdk |

## No keyword overlap

- 1: Pangolin Advertising SDK
- 3: DataFinder analysis
- 5: Ali Mobile Data Analysis
- 6: Ali Mobile push
- 7: Umeng Push Platform
- 8: Tencent Advertising
- 9: Tencent Mobile Push
- 10: Tencent Mobile Analytics
- 12: Tencent Tinker hot update
- 13: Tencent Browser Service (X5 Kernel)
- 14: Getui SDK
- 16: Kuaishou Advertising Alliance
- 17: Bilibili advertisement
- 18: JD CPS Alliance SDK
- 20: Baidu Cloud Push
- 21: Baidu Advertising
- 26: qamob Ads
- 28: Rongyun push
- 31: Xiaomi Push
- 32: Xiaomi Application Check Update SDK
- 33: Meizu message push service
- 34: Vivo message push service
- 35: Vivo Advertising Alliance
- 36: Oppo Push Service
- 37: Oppo Advertising Alliance
- 39: Google DoubleClick
- 44: Xiti
- 77: CrowdTangle
- 100: Google Ads
- 452: WeChat advertisement
- 453: Meizu Ads
- 454: Alibaba Baichuan Advertising
- 455: Tomato Free Novel Advertising Component
- 456: WeChat NFC
- 457: HMS Core Ads SDK
- 458: BeiZi SDK
- 459: Sigmob
- 460: TopOn SDK
- 461: ADSuyi SDK
- 462: Xiaomi Mobile Ads Alliance (Mimo Ad SDK)
- 463: Zooking SDK
- 464: Pinduoduo Rewarded Video Ads
- 465: Sohu In-App Ads
- 466: Honor Ad Alliance

## Ignored trackers

- 363: Pangle includes com.bytedance, the whole ByteDance namespace, which would also match TikTok internals. Keep the specific, reviewed Pangolin keywords instead.
