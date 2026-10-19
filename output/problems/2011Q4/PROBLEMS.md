# PROBLEMS — index 2012Q1

Total logged: 865

## By stage / reason

stage     reason                                            
checksum  entry count off by >2, unexplained                    208
          value scale x1000 (dollars vs thousands)              192
          entry total counts distinct CUSIPs not rows           165
          value off >1%, unexplained                            102
parse     no holdings parsed (text, cusip-lines=0)               51
checksum  no rows parsed                                         32
          entry count off by <=2                                 32
          value within 1% (rounding)                             28
parse     no holdings parsed (text, cusip-lines=1)               14
checksum  entry off by <=2 and value off >1%                     13
          entry off by <=2 and value within 1%                   10
parse     no holdings parsed (text, cusip-lines=2)                2
          no holdings parsed (text, cusip-lines=119)              2
          no holdings parsed (text, cusip-lines=4)                1
          no holdings parsed (text, cusip-lines=610)              1
          no holdings parsed (text, cusip-lines=6)                1
          no holdings parsed (text, cusip-lines=9)                1
          no holdings parsed (text, cusip-lines=54)               1
          no holdings parsed (text, cusip-lines=5)                1
checksum  empty filing (single placeholder row, totals zero)      1
parse     no holdings parsed (text, cusip-lines=307)              1
          no holdings parsed (text, cusip-lines=301)              1
          no holdings parsed (text, cusip-lines=289)              1
          no holdings parsed (text, cusip-lines=184)              1
          no holdings parsed (text, cusip-lines=18)               1
checksum  summary fields swapped (entry total = value total)      1
parse     no holdings parsed (text, cusip-lines=985)              1

## First 200 entries

| stage    | accession            | reason                                             | detail                                                                                           |
|:---------|:---------------------|:---------------------------------------------------|:-------------------------------------------------------------------------------------------------|
| checksum | 0000810672-12-000001 | entry count off by >2, unexplained                 | rows=42 entry_total=53.0 value_sum=153477 value_total=179700500.0 method=text                    |
| checksum | 0001144204-12-008651 | value scale x1000 (dollars vs thousands)           | rows=21 entry_total=21.0 value_sum=73183801 value_total=73184.0 method=text                      |
| checksum | 0001080434-12-000002 | entry off by <=2 and value off >1%                 | rows=650 entry_total=651.0 value_sum=23961227 value_total=26293116.0 method=text                 |
| checksum | 0001511144-12-000002 | value scale x1000 (dollars vs thousands)           | rows=304 entry_total=304.0 value_sum=180295 value_total=180441741.0 method=text                  |
| checksum | 0000080835-12-000002 | entry total counts distinct CUSIPs not rows        | rows=270 entry_total=272.0 value_sum=429024 value_total=429866.0 method=text                     |
| checksum | 0001031972-12-000009 | value off >1%, unexplained                         | rows=38 entry_total=38.0 value_sum=269702503642 value_total=333058000.0 method=text              |
| checksum | 0001135428-12-000032 | entry off by <=2 and value off >1%                 | rows=993 entry_total=994.0 value_sum=10689908 value_total=11098112.0 method=text                 |
| checksum | 0001510940-12-000002 | entry count off by >2, unexplained                 | rows=38 entry_total=43.0 value_sum=170489 value_total=171080.0 method=text                       |
| checksum | 0001134152-12-000002 | value off >1%, unexplained                         | rows=101 entry_total=101.0 value_sum=229482685 value_total=2299482676.0 method=text              |
| checksum | 0000766351-12-000002 | entry count off by >2, unexplained                 | rows=943 entry_total=0.0 value_sum=1817536514 value_total=1828255102.0 method=text               |
| checksum | 0001093589-12-000001 | value scale x1000 (dollars vs thousands)           | rows=66 entry_total=66.0 value_sum=520758 value_total=520854000.0 method=text                    |
| checksum | 0001144204-12-005935 | entry total counts distinct CUSIPs not rows        | rows=90 entry_total=91.0 value_sum=455986 value_total=456031.0 method=text                       |
| checksum | 0001193125-12-038588 | entry total counts distinct CUSIPs not rows        | rows=68 entry_total=57.0 value_sum=816949 value_total=816949.0 method=text                       |
| checksum | 0001011438-12-000132 | entry count off by >2, unexplained                 | rows=53 entry_total=56.0 value_sum=922767 value_total=922767.0 method=text                       |
| checksum | 0001120926-12-000003 | value scale x1000 (dollars vs thousands)           | rows=148 entry_total=148.0 value_sum=935347 value_total=935345933.0 method=text                  |
| checksum | 0000857508-12-000003 | value scale x1000 (dollars vs thousands)           | rows=337 entry_total=337.0 value_sum=1048050 value_total=1048056404.0 method=text                |
| checksum | 0000857538-12-000001 | value scale x1000 (dollars vs thousands)           | rows=342 entry_total=342.0 value_sum=575252 value_total=575257307.0 method=text                  |
| checksum | 0001389848-12-000002 | value off >1%, unexplained                         | rows=41 entry_total=41.0 value_sum=77716 value_total=26023.0 method=text                         |
| checksum | 0001013536-12-000001 | value scale x1000 (dollars vs thousands)           | rows=557 entry_total=557.0 value_sum=18810611 value_total=18811.0 method=text                    |
| checksum | 0001006438-12-000001 | value scale x1000 (dollars vs thousands)           | rows=29 entry_total=29.0 value_sum=764819 value_total=764818000.0 method=text                    |
| checksum | 0001080166-12-000001 | entry total counts distinct CUSIPs not rows        | rows=94 entry_total=95.0 value_sum=177015 value_total=177509.0 method=text                       |
| checksum | 0001144204-12-001514 | entry count off by <=2                             | rows=139 entry_total=140.0 value_sum=6356586 value_total=6356604.0 method=text                   |
| checksum | 0000909012-12-000148 | entry count off by >2, unexplained                 | rows=46 entry_total=49.0 value_sum=26300 value_total=26300.0 method=text                         |
| checksum | 0001193125-12-060124 | entry count off by >2, unexplained                 | rows=166 entry_total=187.0 value_sum=649266000 value_total=734909.0 method=text                  |
| checksum | 0001532155-12-000004 | entry total counts distinct CUSIPs not rows        | rows=3126 entry_total=3127.0 value_sum=92013570 value_total=92665059.0 method=text               |
| checksum | 0001308778-12-000002 | entry total counts distinct CUSIPs not rows        | rows=231 entry_total=232.0 value_sum=148914 value_total=149033.0 method=text                     |
| checksum | 0001520601-12-000002 | value scale x1000 (dollars vs thousands)           | rows=181 entry_total=181.0 value_sum=772071 value_total=722065000.0 method=text                  |
| checksum | 0001541895-12-000001 | value scale x1000 (dollars vs thousands)           | rows=100 entry_total=nan value_sum=382480 value_total=382480000.0 method=text                    |
| checksum | 0001518195-12-000001 | value scale x1000 (dollars vs thousands)           | rows=185 entry_total=185.0 value_sum=138418 value_total=138.0 method=text                        |
| checksum | 0001208646-12-000025 | value scale x1000 (dollars vs thousands)           | rows=38 entry_total=38.0 value_sum=751652256 value_total=751652.0 method=text                    |
| checksum | 0001193125-12-060021 | entry count off by >2, unexplained                 | rows=83 entry_total=90.0 value_sum=977369 value_total=1054475.0 method=text                      |
| checksum | 0001513193-12-000002 | value off >1%, unexplained                         | rows=60 entry_total=60.0 value_sum=2730018 value_total=346445.0 method=text                      |
| checksum | 0000890353-12-000002 | value scale x1000 (dollars vs thousands)           | rows=182 entry_total=182.0 value_sum=298815927 value_total=298816.0 method=text                  |
| checksum | 0001140022-12-000003 | value off >1%, unexplained                         | rows=1097 entry_total=1097.0 value_sum=8399431 value_total=8984886.0 method=text                 |
| checksum | 0001388168-12-000002 | entry count off by >2, unexplained                 | rows=136 entry_total=1.0 value_sum=838466 value_total=836251.0 method=text                       |
| checksum | 0000904454-12-000107 | value off >1%, unexplained                         | rows=152 entry_total=152.0 value_sum=1029633 value_total=1542808.0 method=text                   |
| checksum | 0001398344-12-000521 | value scale x1000 (dollars vs thousands)           | rows=52 entry_total=53.0 value_sum=101 value_total=104385.0 method=text                          |
| checksum | 0001162044-12-000129 | no rows parsed                                     | rows=0 entry_total=328.0 value_sum=0 value_total=305941.0 method=text                            |
| checksum | 0001095449-12-000004 | entry count off by >2, unexplained                 | rows=1263 entry_total=11363.0 value_sum=1830555 value_total=1830549.0 method=text                |
| checksum | 0001353869-12-000001 | value scale x1000 (dollars vs thousands)           | rows=7 entry_total=7.0 value_sum=69931 value_total=69930780.0 method=text                        |
| checksum | 0001088875-12-000012 | value off >1%, unexplained                         | rows=469 entry_total=469.0 value_sum=23400221 value_total=23.0 method=text                       |
| checksum | 0001193125-12-060469 | entry total counts distinct CUSIPs not rows        | rows=8 entry_total=9.0 value_sum=6097779 value_total=6108816.0 method=text                       |
| checksum | 0001074027-12-000001 | value scale x1000 (dollars vs thousands)           | rows=69 entry_total=70.0 value_sum=234456 value_total=234480000.0 method=text                    |
| checksum | 0000810972-12-000002 | value off >1%, unexplained                         | rows=1446 entry_total=1446.0 value_sum=3888658 value_total=0.0 method=text                       |
| checksum | 0001274196-12-000002 | entry count off by >2, unexplained                 | rows=207 entry_total=216.0 value_sum=425548 value_total=438910.0 method=text                     |
| checksum | 0000911274-12-000001 | entry total counts distinct CUSIPs not rows        | rows=137 entry_total=138.0 value_sum=194646 value_total=195112.0 method=text                     |
| checksum | 0001096783-12-000002 | value scale x1000 (dollars vs thousands)           | rows=64 entry_total=nan value_sum=106828 value_total=110391000.0 method=text                     |
| checksum | 0001509445-12-000001 | value scale x1000 (dollars vs thousands)           | rows=23 entry_total=23.0 value_sum=494089 value_total=494088000.0 method=text                    |
| checksum | 0001079738-12-000001 | entry count off by >2, unexplained                 | rows=56 entry_total=1.0 value_sum=154461 value_total=154462.0 method=text                        |
| checksum | 0000918504-12-000002 | entry count off by >2, unexplained                 | rows=103 entry_total=1.0 value_sum=213025 value_total=nan method=text                            |
| checksum | 0001193125-12-060928 | entry count off by >2, unexplained                 | rows=34 entry_total=101.0 value_sum=25308882 value_total=66151587.0 method=text                  |
| checksum | 0000893838-12-000007 | entry count off by >2, unexplained                 | rows=3156 entry_total=7.0 value_sum=1806504 value_total=7394360.0 method=text                    |
| checksum | 0000893838-12-000014 | no rows parsed                                     | rows=0 entry_total=3.0 value_sum=0 value_total=0.0 method=text                                   |
| checksum | 0000748054-12-000002 | value off >1%, unexplained                         | rows=1560 entry_total=1560.0 value_sum=938521958497154 value_total=60732675.0 method=text        |
| checksum | 0001042046-12-000001 | value off >1%, unexplained                         | rows=163 entry_total=163.0 value_sum=993878 value_total=1009673.0 method=text                    |
| checksum | 0001193125-12-048545 | value scale x1000 (dollars vs thousands)           | rows=8094 entry_total=8094.0 value_sum=9130100149 value_total=9130100.0 method=text              |
| checksum | 0001140361-12-003751 | entry off by <=2 and value off >1%                 | rows=120 entry_total=122.0 value_sum=177047 value_total=178862.0 method=text                     |
| checksum | 0000904163-12-000001 | value scale x1000 (dollars vs thousands)           | rows=319 entry_total=319.0 value_sum=1072864 value_total=1073.0 method=text                      |
| checksum | 0001193125-12-060577 | entry count off by <=2                             | rows=7252 entry_total=7254.0 value_sum=131077906 value_total=131077906.0 method=text             |
| checksum | 0000829937-12-000002 | entry total counts distinct CUSIPs not rows        | rows=296 entry_total=297.0 value_sum=3952857 value_total=3960658.0 method=text                   |
| checksum | 0001121477-12-000001 | entry total counts distinct CUSIPs not rows        | rows=206 entry_total=207.0 value_sum=116887 value_total=117272.0 method=text                     |
| checksum | 0000872162-12-000002 | no rows parsed                                     | rows=0 entry_total=117.0 value_sum=0 value_total=455693.0 method=text                            |
| checksum | 0001169738-12-000001 | entry total counts distinct CUSIPs not rows        | rows=190 entry_total=191.0 value_sum=320641 value_total=322534.0 method=text                     |
| checksum | 0001140361-12-006162 | entry count off by >2, unexplained                 | rows=1719 entry_total=1732.0 value_sum=40276610 value_total=39037855.0 method=text               |
| checksum | 0001360798-12-000001 | entry total counts distinct CUSIPs not rows        | rows=101 entry_total=100.0 value_sum=321616 value_total=321616.0 method=text                     |
| checksum | 0001085146-12-000017 | entry off by <=2 and value off >1%                 | rows=61 entry_total=63.0 value_sum=5479579 value_total=5209477.0 method=text                     |
| checksum | 0001228242-12-000003 | no rows parsed                                     | rows=0 entry_total=610.0 value_sum=0 value_total=nan method=text                                 |
| checksum | 0001089212-12-000003 | value scale x1000 (dollars vs thousands)           | rows=129 entry_total=129.0 value_sum=927359 value_total=927353000.0 method=text                  |
| checksum | 0001047339-12-000002 | entry count off by >2, unexplained                 | rows=126 entry_total=132.0 value_sum=183239 value_total=183772.0 method=text                     |
| checksum | 0001106544-12-000002 | value scale x1000 (dollars vs thousands)           | rows=47 entry_total=47.0 value_sum=174463 value_total=174461811.0 method=text                    |
| checksum | 0001193125-12-060360 | value scale x1000 (dollars vs thousands)           | rows=48 entry_total=48.0 value_sum=4166819279 value_total=4166819.0 method=text                  |
| checksum | 0001144204-12-009228 | entry count off by >2, unexplained                 | rows=425 entry_total=290199182.0 value_sum=11036215 value_total=11372059.0 method=text           |
| checksum | 0001352859-12-000002 | value scale x1000 (dollars vs thousands)           | rows=127 entry_total=127.0 value_sum=139008 value_total=139012000.0 method=text                  |
| checksum | 0001455126-12-000001 | no rows parsed                                     | rows=0 entry_total=302.0 value_sum=0 value_total=73405.0 method=text                             |
| checksum | 0001388142-12-000002 | entry total counts distinct CUSIPs not rows        | rows=38 entry_total=40.0 value_sum=146432 value_total=153885.0 method=text                       |
| checksum | 0001482852-12-000002 | entry count off by >2, unexplained                 | rows=14 entry_total=2.0 value_sum=378398 value_total=nan method=text                             |
| checksum | 0000811393-12-000001 | entry count off by >2, unexplained                 | rows=526 entry_total=263.0 value_sum=207622 value_total=103811.0 method=text                     |
| checksum | 0000312069-12-000036 | entry count off by >2, unexplained                 | rows=15600 entry_total=75661005.0 value_sum=75661005 value_total=15600.0 method=text             |
| checksum | 0000934729-12-000025 | entry total counts distinct CUSIPs not rows        | rows=9800 entry_total=3503.0 value_sum=54771970 value_total=54771970.0 method=text               |
| checksum | 0001520354-12-000001 | value scale x1000 (dollars vs thousands)           | rows=1676 entry_total=1676.0 value_sum=18214 value_total=18256174.0 method=text                  |
| checksum | 0000950156-12-000001 | entry off by <=2 and value within 1%               | rows=61 entry_total=63.0 value_sum=77439 value_total=77752.0 method=text                         |
| checksum | 0001193125-12-011448 | entry count off by >2, unexplained                 | rows=279 entry_total=284.0 value_sum=884538 value_total=896838.0 method=text                     |
| checksum | 0000070858-12-000148 | value off >1%, unexplained                         | rows=16965 entry_total=16965.0 value_sum=1121748980089419 value_total=168563853000.0 method=text |
| checksum | 0000315080-12-000002 | entry count off by >2, unexplained                 | rows=448 entry_total=423.0 value_sum=749209 value_total=692371.0 method=text                     |
| checksum | 0001483472-12-000002 | entry count off by >2, unexplained                 | rows=91 entry_total=98.0 value_sum=78789 value_total=87359.0 method=text                         |
| checksum | 0001398344-12-000425 | no rows parsed                                     | rows=0 entry_total=183.0 value_sum=0 value_total=221735.0 method=text                            |
| checksum | 0001313998-12-000001 | entry total counts distinct CUSIPs not rows        | rows=34 entry_total=35.0 value_sum=28364 value_total=28510.0 method=text                         |
| checksum | 0001510320-12-000002 | entry total counts distinct CUSIPs not rows        | rows=259 entry_total=258.0 value_sum=272953 value_total=272954.0 method=text                     |
| checksum | 0001317829-12-000002 | entry total counts distinct CUSIPs not rows        | rows=43 entry_total=44.0 value_sum=8427 value_total=8504.0 method=text                           |
| checksum | 0001047469-12-000892 | entry count off by >2, unexplained                 | rows=317 entry_total=303.0 value_sum=528999 value_total=498869.0 method=text                     |
| checksum | 0000860828-12-000001 | value scale x1000 (dollars vs thousands)           | rows=89 entry_total=89.0 value_sum=228284231 value_total=228284.0 method=text                    |
| checksum | 0001193125-12-050725 | entry count off by >2, unexplained                 | rows=1416 entry_total=1439.0 value_sum=5498708 value_total=5765755.0 method=text                 |
| checksum | 0001019687-12-000423 | entry count off by >2, unexplained                 | rows=75 entry_total=81.0 value_sum=192538 value_total=195915.0 method=text                       |
| checksum | 0001144204-12-006989 | entry total counts distinct CUSIPs not rows        | rows=835 entry_total=834.0 value_sum=11686681 value_total=11687089.0 method=text                 |
| checksum | 0001140361-12-010966 | entry count off by >2, unexplained                 | rows=282 entry_total=286.0 value_sum=392270 value_total=401083.0 method=text                     |
| checksum | 0000825293-12-000002 | entry total counts distinct CUSIPs not rows        | rows=115 entry_total=114.0 value_sum=56810 value_total=56273.0 method=text                       |
| checksum | 0001074273-12-000001 | value scale x1000 (dollars vs thousands)           | rows=54 entry_total=54.0 value_sum=186642087 value_total=186642.0 method=text                    |
| checksum | 0000945621-12-000036 | value scale x1000 (dollars vs thousands)           | rows=1475 entry_total=1475.0 value_sum=2211517 value_total=2211517000.0 method=text              |
| checksum | 0001276755-12-000002 | value scale x1000 (dollars vs thousands)           | rows=105 entry_total=105.0 value_sum=350021 value_total=350024164.0 method=text                  |
| checksum | 0001193125-12-024509 | entry total counts distinct CUSIPs not rows        | rows=203 entry_total=204.0 value_sum=502170 value_total=502514.0 method=text                     |
| checksum | 0001455176-12-000002 | entry count off by >2, unexplained                 | rows=90 entry_total=74.0 value_sum=239263 value_total=239479.0 method=text                       |
| checksum | 0001276460-12-000001 | entry count off by >2, unexplained                 | rows=88 entry_total=93.0 value_sum=560932 value_total=563588.0 method=text                       |
| checksum | 0000019475-12-000001 | value scale x1000 (dollars vs thousands)           | rows=91 entry_total=91.0 value_sum=560726 value_total=560726000.0 method=text                    |
| checksum | 0001163648-12-000007 | value within 1% (rounding)                         | rows=293 entry_total=293.0 value_sum=8454984 value_total=8431665.0 method=text                   |
| checksum | 0001421224-12-000001 | entry count off by >2, unexplained                 | rows=310 entry_total=336.0 value_sum=12963168 value_total=31760596.0 method=text                 |
| checksum | 0001072613-12-000112 | entry total counts distinct CUSIPs not rows        | rows=87 entry_total=88.0 value_sum=1679564 value_total=1679801.0 method=text                     |
| checksum | 0001080071-12-000002 | value within 1% (rounding)                         | rows=123 entry_total=123.0 value_sum=121710 value_total=120994.0 method=text                     |
| checksum | 0001284812-12-000103 | entry count off by <=2                             | rows=447 entry_total=449.0 value_sum=26616842 value_total=26616847.0 method=text                 |
| checksum | 0001193125-12-052170 | value scale x1000 (dollars vs thousands)           | rows=326 entry_total=326.0 value_sum=20504938 value_total=20504934000.0 method=text              |
| checksum | 0001086364-12-002181 | value within 1% (rounding)                         | rows=8350 entry_total=8350.0 value_sum=48215801 value_total=48291797.0 method=text               |
| checksum | 0001141455-12-000001 | value scale x1000 (dollars vs thousands)           | rows=98 entry_total=98.0 value_sum=314014 value_total=314014000.0 method=text                    |
| checksum | 0001193125-12-090799 | value scale x1000 (dollars vs thousands)           | rows=750 entry_total=752.0 value_sum=122708 value_total=123083880.0 method=text                  |
| checksum | 0001140804-12-000002 | entry count off by >2, unexplained                 | rows=474 entry_total=267718558.0 value_sum=7660541025 value_total=7662246210.0 method=text       |
| checksum | 0001193125-12-011405 | value scale x1000 (dollars vs thousands)           | rows=141 entry_total=141.0 value_sum=359492 value_total=359557246.0 method=text                  |
| checksum | 0001047469-12-000895 | entry total counts distinct CUSIPs not rows        | rows=104 entry_total=105.0 value_sum=378995 value_total=381985.0 method=text                     |
| checksum | 0001166880-12-000002 | entry count off by >2, unexplained                 | rows=89 entry_total=176.0 value_sum=97421 value_total=178273.0 method=text                       |
| checksum | 0000891118-12-000002 | value scale x1000 (dollars vs thousands)           | rows=38 entry_total=38.0 value_sum=363725000 value_total=363708.0 method=text                    |
| checksum | 0001144204-12-000552 | value scale x1000 (dollars vs thousands)           | rows=76 entry_total=76.0 value_sum=234638215 value_total=234638.0 method=text                    |
| checksum | 0001015247-12-000001 | entry count off by >2, unexplained                 | rows=306 entry_total=310.0 value_sum=509342 value_total=477039.0 method=text                     |
| checksum | 0000909012-12-000158 | value off >1%, unexplained                         | rows=170 entry_total=170.0 value_sum=530 value_total=593.0 method=text                           |
| checksum | 0001492166-12-000002 | entry count off by >2, unexplained                 | rows=342 entry_total=1.0 value_sum=269464 value_total=nan method=text                            |
| checksum | 0001483499-12-000001 | value off >1%, unexplained                         | rows=186 entry_total=186.0 value_sum=50593193791 value_total=368791.0 method=text                |
| checksum | 0001340807-12-000013 | value off >1%, unexplained                         | rows=69 entry_total=69.0 value_sum=22204464 value_total=389505.0 method=text                     |
| checksum | 0001353198-12-000001 | entry total counts distinct CUSIPs not rows        | rows=43 entry_total=45.0 value_sum=266515 value_total=268257.0 method=text                       |
| checksum | 0001193125-12-067900 | entry off by <=2 and value within 1%               | rows=477 entry_total=476.0 value_sum=21453427 value_total=21315519.0 method=text                 |
| checksum | 0001542166-12-000001 | value scale x1000 (dollars vs thousands)           | rows=37 entry_total=37.0 value_sum=126674 value_total=126695026.0 method=text                    |
| checksum | 0001348886-12-000002 | entry total counts distinct CUSIPs not rows        | rows=37 entry_total=39.0 value_sum=170229 value_total=182454.0 method=text                       |
| checksum | 0001444043-12-000005 | entry off by <=2 and value off >1%                 | rows=45 entry_total=47.0 value_sum=737962 value_total=769374.0 method=text                       |
| checksum | 0001388549-12-000002 | entry count off by >2, unexplained                 | rows=193 entry_total=1435.0 value_sum=311051402 value_total=373204.0 method=text                 |
| checksum | 0001193125-12-028767 | entry count off by >2, unexplained                 | rows=552 entry_total=558.0 value_sum=4718207 value_total=4735587.0 method=text                   |
| checksum | 0001193125-12-063008 | value within 1% (rounding)                         | rows=98 entry_total=98.0 value_sum=257479 value_total=256889.0 method=text                       |
| checksum | 0000902664-12-000450 | value off >1%, unexplained                         | rows=43 entry_total=43.0 value_sum=321290 value_total=984808.0 method=text                       |
| checksum | 0000909518-12-000046 | value scale x1000 (dollars vs thousands)           | rows=2 entry_total=2.0 value_sum=233644653 value_total=233644.0 method=text                      |
| checksum | 0000909518-12-000047 | value scale x1000 (dollars vs thousands)           | rows=3 entry_total=3.0 value_sum=120293297 value_total=120293.0 method=text                      |
| checksum | 0001510870-12-000001 | entry total counts distinct CUSIPs not rows        | rows=52 entry_total=53.0 value_sum=30417 value_total=30417.0 method=text                         |
| checksum | 0001454335-12-000002 | empty filing (single placeholder row, totals zero) | rows=1 entry_total=0.0 value_sum=0 value_total=0.0 method=text                                   |
| checksum | 0001047469-12-001012 | value scale x1000 (dollars vs thousands)           | rows=84 entry_total=84.0 value_sum=1365360 value_total=1365.0 method=text                        |
| checksum | 0001140361-12-007555 | entry count off by >2, unexplained                 | rows=12 entry_total=21.0 value_sum=20915 value_total=189772.0 method=text                        |
| checksum | 0001381066-12-000001 | value off >1%, unexplained                         | rows=106 entry_total=106.0 value_sum=236972 value_total=234036.0 method=text                     |
| checksum | 0001454968-12-000002 | entry count off by <=2                             | rows=199 entry_total=200.0 value_sum=341627 value_total=341484.0 method=text                     |
| checksum | 0001085146-12-000345 | entry count off by <=2                             | rows=396 entry_total=397.0 value_sum=309721 value_total=309721.0 method=text                     |
| checksum | 0001317172-12-000012 | value scale x1000 (dollars vs thousands)           | rows=5 entry_total=5.0 value_sum=60585 value_total=60587158.0 method=text                        |
| checksum | 0001163744-12-000001 | entry total counts distinct CUSIPs not rows        | rows=112 entry_total=111.0 value_sum=533617 value_total=533617.0 method=text                     |
| checksum | 0001542153-12-000002 | value scale x1000 (dollars vs thousands)           | rows=127 entry_total=127.0 value_sum=461942 value_total=462007000.0 method=text                  |
| checksum | 0001333978-12-000002 | entry count off by >2, unexplained                 | rows=1578 entry_total=1581.0 value_sum=3834228 value_total=3836556.0 method=text                 |
| checksum | 0001135428-12-000034 | entry count off by >2, unexplained                 | rows=385 entry_total=393.0 value_sum=749533 value_total=760338.0 method=text                     |
| checksum | 0000891092-12-000989 | entry count off by >2, unexplained                 | rows=150 entry_total=153.0 value_sum=785123257 value_total=785088902.0 method=text               |
| checksum | 0001193125-12-061444 | value scale x1000 (dollars vs thousands)           | rows=118 entry_total=118.0 value_sum=6613301 value_total=6613.0 method=text                      |
| checksum | 0001422219-12-000002 | entry total counts distinct CUSIPs not rows        | rows=110 entry_total=111.0 value_sum=671949 value_total=672049.0 method=text                     |
| checksum | 0001323119-12-000001 | value scale x1000 (dollars vs thousands)           | rows=204 entry_total=204.0 value_sum=681569 value_total=681567000.0 method=text                  |
| checksum | 0001036325-12-000004 | value off >1%, unexplained                         | rows=274 entry_total=274.0 value_sum=45864729 value_total=45.0 method=text                       |
| checksum | 0001144204-12-003153 | entry count off by <=2                             | rows=323 entry_total=324.0 value_sum=386436 value_total=386533.0 method=text                     |
| checksum | 0000767684-12-000002 | value scale x1000 (dollars vs thousands)           | rows=140 entry_total=140.0 value_sum=541581 value_total=541581000.0 method=text                  |
| checksum | 0001353098-12-000003 | entry total counts distinct CUSIPs not rows        | rows=75 entry_total=76.0 value_sum=176913 value_total=177227.0 method=text                       |
| checksum | 0001406995-12-000002 | entry total counts distinct CUSIPs not rows        | rows=184 entry_total=185.0 value_sum=164114 value_total=165216.0 method=text                     |
| checksum | 0001058217-12-000004 | value scale x1000 (dollars vs thousands)           | rows=44 entry_total=44.0 value_sum=21038 value_total=21037226.0 method=text                      |
| checksum | 0000887777-12-000001 | value off >1%, unexplained                         | rows=467 entry_total=467.0 value_sum=7701924 value_total=2697798.0 method=text                   |
| checksum | 0001080107-12-000001 | value scale x1000 (dollars vs thousands)           | rows=3833 entry_total=3833.0 value_sum=1592055 value_total=1592055000.0 method=text              |
| checksum | 0001140771-12-000002 | value scale x1000 (dollars vs thousands)           | rows=725 entry_total=725.0 value_sum=631623 value_total=631623000.0 method=text                  |
| checksum | 0000910472-12-000349 | entry total counts distinct CUSIPs not rows        | rows=514 entry_total=515.0 value_sum=317205 value_total=317205.0 method=text                     |
| checksum | 0000893738-12-000001 | value scale x1000 (dollars vs thousands)           | rows=49 entry_total=49.0 value_sum=112190 value_total=112190000.0 method=text                    |
| checksum | 0001145935-12-000003 | entry count off by >2, unexplained                 | rows=110 entry_total=262.0 value_sum=914158 value_total=2360029.0 method=text                    |
| checksum | 0001142941-12-000001 | entry total counts distinct CUSIPs not rows        | rows=319 entry_total=318.0 value_sum=773172 value_total=863762.0 method=text                     |
| checksum | 0001014909-12-000001 | entry count off by >2, unexplained                 | rows=497 entry_total=331288089.0 value_sum=4075626 value_total=4075631.0 method=text             |
| checksum | 0000936936-12-000001 | value scale x1000 (dollars vs thousands)           | rows=90 entry_total=82.0 value_sum=149168 value_total=137686000.0 method=text                    |
| checksum | 0000938077-12-000004 | value off >1%, unexplained                         | rows=214 entry_total=214.0 value_sum=16652893 value_total=154271.0 method=text                   |
| checksum | 0000814375-12-000001 | value off >1%, unexplained                         | rows=97 entry_total=97.0 value_sum=4267795 value_total=3242.0 method=text                        |
| checksum | 0001110443-12-000004 | entry count off by >2, unexplained                 | rows=159 entry_total=154.0 value_sum=11993162775 value_total=92999.0 method=text                 |
| checksum | 0001193125-12-026194 | entry count off by >2, unexplained                 | rows=5442 entry_total=5453.0 value_sum=10944594 value_total=10772539.0 method=text               |
| checksum | 0000909012-12-000160 | entry count off by >2, unexplained                 | rows=699 entry_total=768.0 value_sum=171392939 value_total=346890.0 method=text                  |
| checksum | 0001193125-12-056351 | no rows parsed                                     | rows=0 entry_total=4.0 value_sum=0 value_total=563037.0 method=text                              |
| checksum | 0000831001-12-000076 | value scale x1000 (dollars vs thousands)           | rows=12883 entry_total=12883.0 value_sum=92568269 value_total=92568276453.0 method=text          |
| checksum | 0001050442-12-000002 | entry total counts distinct CUSIPs not rows        | rows=101 entry_total=102.0 value_sum=2231970 value_total=2232038.0 method=text                   |
| checksum | 0001085146-12-000246 | entry total counts distinct CUSIPs not rows        | rows=116 entry_total=110.0 value_sum=622706 value_total=622705.0 method=text                     |
| checksum | 0001193125-12-056726 | value scale x1000 (dollars vs thousands)           | rows=77 entry_total=85.0 value_sum=3341229 value_total=3341229000.0 method=text                  |
| checksum | 0001193125-12-028849 | value scale x1000 (dollars vs thousands)           | rows=30 entry_total=31.0 value_sum=151743596 value_total=151744.0 method=text                    |
| checksum | 0000920112-12-000012 | entry total counts distinct CUSIPs not rows        | rows=430 entry_total=317.0 value_sum=253809447 value_total=253870879.0 method=text               |
| checksum | 0000883511-12-000001 | entry count off by >2, unexplained                 | rows=30 entry_total=1.0 value_sum=374621 value_total=nan method=text                             |
| checksum | 0001435346-12-000003 | entry total counts distinct CUSIPs not rows        | rows=139 entry_total=138.0 value_sum=1001302 value_total=1001292.0 method=text                   |
| checksum | 0001481045-12-000001 | value off >1%, unexplained                         | rows=1610 entry_total=1610.0 value_sum=13051052 value_total=13223813.0 method=text               |
| checksum | 0001510809-12-000002 | entry total counts distinct CUSIPs not rows        | rows=54 entry_total=53.0 value_sum=73393 value_total=72636.0 method=text                         |
| checksum | 0001047469-12-000897 | entry total counts distinct CUSIPs not rows        | rows=89 entry_total=67.0 value_sum=78637 value_total=78636.0 method=text                         |
| checksum | 0001479844-12-000002 | entry off by <=2 and value within 1%               | rows=1082 entry_total=1084.0 value_sum=682130 value_total=683673.0 method=text                   |
| checksum | 0001193125-12-043489 | value scale x1000 (dollars vs thousands)           | rows=336 entry_total=336.0 value_sum=2485485522 value_total=2485486.0 method=text                |
| checksum | 0001384042-12-000002 | entry total counts distinct CUSIPs not rows        | rows=659 entry_total=182.0 value_sum=250583 value_total=250563.0 method=text                     |
| checksum | 0001308527-12-000001 | value off >1%, unexplained                         | rows=168 entry_total=168.0 value_sum=735862546633 value_total=659255579.0 method=text            |
| checksum | 0001140361-12-007765 | entry off by <=2 and value off >1%                 | rows=129 entry_total=130.0 value_sum=2991325 value_total=2923204.0 method=text                   |
| checksum | 0001085146-12-000208 | value off >1%, unexplained                         | rows=1484 entry_total=1484.0 value_sum=43806101843976 value_total=309782.0 method=text           |
| checksum | 0001013538-12-000002 | value off >1%, unexplained                         | rows=61 entry_total=61.0 value_sum=1206431 value_total=120643.0 method=text                      |
| checksum | 0000945631-12-000004 | value scale x1000 (dollars vs thousands)           | rows=55 entry_total=55.0 value_sum=10116513 value_total=10116511000.0 method=text                |
| checksum | 0001107799-12-000001 | entry count off by >2, unexplained                 | rows=88 entry_total=345.0 value_sum=18901 value_total=71622.0 method=text                        |
| checksum | 0001082970-12-000002 | value scale x1000 (dollars vs thousands)           | rows=500 entry_total=500.0 value_sum=3584210 value_total=3584210000.0 method=text                |
| checksum | 0001386088-12-000001 | no rows parsed                                     | rows=0 entry_total=26.0 value_sum=0 value_total=2764229.0 method=text                            |
| checksum | 0001542164-12-000002 | no rows parsed                                     | rows=0 entry_total=18.0 value_sum=0 value_total=225877.0 method=text                             |
| checksum | 0001260824-12-000001 | value off >1%, unexplained                         | rows=122 entry_total=122.0 value_sum=406591 value_total=15209437.0 method=text                   |
| checksum | 0000902664-12-000316 | value off >1%, unexplained                         | rows=85 entry_total=85.0 value_sum=249055 value_total=240514.0 method=text                       |
| checksum | 0001344717-12-000001 | value off >1%, unexplained                         | rows=212 entry_total=212.0 value_sum=1600053198 value_total=1600.0 method=text                   |
| checksum | 0001321711-12-000022 | value scale x1000 (dollars vs thousands)           | rows=59 entry_total=59.0 value_sum=799181424 value_total=799181.0 method=text                    |
| checksum | 0001193125-12-016460 | entry total counts distinct CUSIPs not rows        | rows=123 entry_total=124.0 value_sum=282588 value_total=282748.0 method=text                     |
| checksum | 0001141911-12-000002 | no rows parsed                                     | rows=0 entry_total=58.0 value_sum=0 value_total=228192.0 method=text                             |