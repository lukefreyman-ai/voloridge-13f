# PROBLEMS — index 2012Q2

Total logged: 868

## By stage / reason

stage     reason                                            
checksum  entry count off by >2, unexplained                    243
          value scale x1000 (dollars vs thousands)              179
          entry total counts distinct CUSIPs not rows           138
          value off >1%, unexplained                            111
parse     no holdings parsed (text, cusip-lines=0)               46
checksum  value within 1% (rounding)                             40
          entry count off by <=2                                 34
          no rows parsed                                         25
          entry off by <=2 and value off >1%                     20
          entry off by <=2 and value within 1%                   10
parse     no holdings parsed (text, cusip-lines=1)                6
          no holdings parsed (text, cusip-lines=616)              1
          no holdings parsed (text, cusip-lines=354)              1
          no holdings parsed (text, cusip-lines=6)                1
          no holdings parsed (text, cusip-lines=58)               1
          no holdings parsed (text, cusip-lines=57)               1
          no holdings parsed (text, cusip-lines=56)               1
          no holdings parsed (text, cusip-lines=5)                1
          no holdings parsed (text, cusip-lines=127)              1
          no holdings parsed (text, cusip-lines=33)               1
          no holdings parsed (text, cusip-lines=217)              1
          no holdings parsed (text, cusip-lines=199)              1
          no holdings parsed (text, cusip-lines=18)               1
          no holdings parsed (text, cusip-lines=142)              1
          no holdings parsed (text, cusip-lines=119)              1
checksum  summary fields swapped (entry total = value total)      1
parse     no holdings parsed (text, cusip-lines=9)                1

## First 200 entries

| stage    | accession            | reason                                      | detail                                                                                     |
|:---------|:---------------------|:--------------------------------------------|:-------------------------------------------------------------------------------------------|
| checksum | 0001511144-12-000004 | value scale x1000 (dollars vs thousands)    | rows=335 entry_total=335.0 value_sum=198679 value_total=198845366.0 method=text            |
| checksum | 0000080835-12-000003 | entry total counts distinct CUSIPs not rows | rows=195 entry_total=197.0 value_sum=463738 value_total=472923.0 method=text               |
| checksum | 0000810672-12-000002 | entry count off by >2, unexplained          | rows=43 entry_total=55.0 value_sum=171346 value_total=197389262.0 method=text              |
| checksum | 0001144204-12-028602 | value scale x1000 (dollars vs thousands)    | rows=28 entry_total=28.0 value_sum=107054419 value_total=107054.0 method=text              |
| checksum | 0001080434-12-000013 | entry off by <=2 and value off >1%          | rows=650 entry_total=651.0 value_sum=25380680 value_total=30513285.0 method=text           |
| checksum | 0001038661-12-000002 | entry total counts distinct CUSIPs not rows | rows=81 entry_total=82.0 value_sum=175379 value_total=175379.0 method=text                 |
| checksum | 0001031972-12-000013 | value off >1%, unexplained                  | rows=37 entry_total=37.0 value_sum=1001506722 value_total=331129000.0 method=text          |
| checksum | 0001135428-12-000229 | entry off by <=2 and value within 1%        | rows=1063 entry_total=1064.0 value_sum=12840562 value_total=12821143.0 method=text         |
| checksum | 0001510940-12-000003 | entry total counts distinct CUSIPs not rows | rows=44 entry_total=45.0 value_sum=195333 value_total=195823.0 method=text                 |
| checksum | 0001019687-12-001792 | entry total counts distinct CUSIPs not rows | rows=136 entry_total=135.0 value_sum=564109 value_total=564111.0 method=text               |
| checksum | 0000766351-12-000033 | entry count off by >2, unexplained          | rows=944 entry_total=0.0 value_sum=2069526076 value_total=2080244642.0 method=text         |
| checksum | 0001093589-12-000002 | value scale x1000 (dollars vs thousands)    | rows=67 entry_total=67.0 value_sum=589643 value_total=589916000.0 method=text              |
| checksum | 0001080166-12-000002 | entry total counts distinct CUSIPs not rows | rows=95 entry_total=96.0 value_sum=191574 value_total=192130.0 method=text                 |
| checksum | 0001120926-12-000005 | value scale x1000 (dollars vs thousands)    | rows=152 entry_total=152.0 value_sum=1144045 value_total=1144047207.0 method=text          |
| checksum | 0000857508-12-000009 | value scale x1000 (dollars vs thousands)    | rows=336 entry_total=336.0 value_sum=1113767 value_total=1113771139.0 method=text          |
| checksum | 0000857538-12-000002 | value scale x1000 (dollars vs thousands)    | rows=341 entry_total=341.0 value_sum=624611 value_total=624608081.0 method=text            |
| checksum | 0001389848-12-000004 | value off >1%, unexplained                  | rows=43 entry_total=43.0 value_sum=81331 value_total=29635.0 method=text                   |
| checksum | 0001006438-12-000005 | value scale x1000 (dollars vs thousands)    | rows=53 entry_total=53.0 value_sum=4052381 value_total=4052383000.0 method=text            |
| checksum | 0001193125-12-231619 | entry total counts distinct CUSIPs not rows | rows=75 entry_total=57.0 value_sum=595042 value_total=595040.0 method=text                 |
| checksum | 0000897070-12-000006 | entry total counts distinct CUSIPs not rows | rows=143 entry_total=144.0 value_sum=569832 value_total=571877.0 method=text               |
| checksum | 0001013536-12-000008 | value scale x1000 (dollars vs thousands)    | rows=523 entry_total=523.0 value_sum=20419611 value_total=20420.0 method=text              |
| checksum | 0001144204-12-021058 | entry count off by <=2                      | rows=148 entry_total=149.0 value_sum=6243696 value_total=6243710.0 method=text             |
| checksum | 0001193125-12-234540 | value scale x1000 (dollars vs thousands)    | rows=404 entry_total=405.0 value_sum=2358284000 value_total=2375777.0 method=text          |
| checksum | 0001518364-12-000005 | entry count off by >2, unexplained          | rows=47 entry_total=43.0 value_sum=211485 value_total=202488.0 method=text                 |
| checksum | 0001140022-12-000009 | value off >1%, unexplained                  | rows=1068 entry_total=1068.0 value_sum=8990648 value_total=9526250.0 method=text           |
| checksum | 0000909012-12-000266 | entry count off by >2, unexplained          | rows=61 entry_total=64.0 value_sum=26824 value_total=26825.0 method=text                   |
| checksum | 0001520601-12-000004 | value scale x1000 (dollars vs thousands)    | rows=176 entry_total=176.0 value_sum=962852 value_total=962858000.0 method=text            |
| checksum | 0001164691-12-000029 | entry off by <=2 and value within 1%        | rows=335 entry_total=336.0 value_sum=3810436 value_total=3818276.0 method=text             |
| checksum | 0001308778-12-000003 | entry total counts distinct CUSIPs not rows | rows=245 entry_total=246.0 value_sum=175655 value_total=175778.0 method=text               |
| checksum | 0001389256-12-000008 | entry total counts distinct CUSIPs not rows | rows=103 entry_total=102.0 value_sum=179360 value_total=179359.0 method=text               |
| checksum | 0001541895-12-000002 | value scale x1000 (dollars vs thousands)    | rows=100 entry_total=nan value_sum=382480 value_total=413942000.0 method=text              |
| checksum | 0001208646-12-000095 | value scale x1000 (dollars vs thousands)    | rows=39 entry_total=39.0 value_sum=536242268 value_total=536242.0 method=text              |
| checksum | 0001193125-12-228302 | entry count off by >2, unexplained          | rows=87 entry_total=98.0 value_sum=863928 value_total=969511.0 method=text                 |
| checksum | 0000904163-12-000002 | value scale x1000 (dollars vs thousands)    | rows=324 entry_total=324.0 value_sum=1170490 value_total=1170.0 method=text                |
| checksum | 0001518195-12-000002 | value scale x1000 (dollars vs thousands)    | rows=186 entry_total=186.0 value_sum=152632 value_total=153.0 method=text                  |
| checksum | 0001502826-12-000001 | value off >1%, unexplained                  | rows=66 entry_total=66.0 value_sum=2700213 value_total=353032.0 method=text                |
| checksum | 0000909012-12-000221 | no rows parsed                              | rows=0 entry_total=16.0 value_sum=0 value_total=136492.0 method=text                       |
| checksum | 0001388168-12-000003 | entry count off by >2, unexplained          | rows=121 entry_total=1.0 value_sum=824093 value_total=836251.0 method=text                 |
| checksum | 0001398344-12-001823 | entry total counts distinct CUSIPs not rows | rows=56 entry_total=57.0 value_sum=121183 value_total=121739.0 method=text                 |
| checksum | 0001193125-12-229996 | value off >1%, unexplained                  | rows=337 entry_total=337.0 value_sum=35823703 value_total=36399951.0 method=text           |
| checksum | 0001144204-12-022398 | entry total counts distinct CUSIPs not rows | rows=96 entry_total=97.0 value_sum=275835 value_total=275835.0 method=text                 |
| checksum | 0000748054-12-000004 | value off >1%, unexplained                  | rows=1561 entry_total=1561.0 value_sum=626240680316743 value_total=69619983.0 method=text  |
| checksum | 0001042046-12-000005 | value off >1%, unexplained                  | rows=179 entry_total=179.0 value_sum=1075053 value_total=1090939.0 method=text             |
| checksum | 0001193125-12-234679 | value scale x1000 (dollars vs thousands)    | rows=8348 entry_total=8348.0 value_sum=12688965863 value_total=12688965.0 method=text      |
| checksum | 0001162044-12-000443 | entry total counts distinct CUSIPs not rows | rows=419 entry_total=347.0 value_sum=479649 value_total=362468.0 method=text               |
| checksum | 0001144204-12-029723 | entry total counts distinct CUSIPs not rows | rows=63 entry_total=61.0 value_sum=3743364 value_total=nan method=text                     |
| checksum | 0001274196-12-000003 | entry count off by >2, unexplained          | rows=208 entry_total=218.0 value_sum=469778 value_total=500089.0 method=text               |
| checksum | 0001088875-12-000016 | value off >1%, unexplained                  | rows=482 entry_total=482.0 value_sum=28098272 value_total=28.0 method=text                 |
| checksum | 0001074027-12-000002 | value scale x1000 (dollars vs thousands)    | rows=81 entry_total=81.0 value_sum=261031 value_total=261033000.0 method=text              |
| checksum | 0000810972-12-000004 | value off >1%, unexplained                  | rows=1526 entry_total=1526.0 value_sum=4519006 value_total=0.0 method=text                 |
| checksum | 0001096783-12-000004 | value scale x1000 (dollars vs thousands)    | rows=66 entry_total=nan value_sum=112115 value_total=117071000.0 method=text               |
| checksum | 0001521536-12-000416 | value off >1%, unexplained                  | rows=1 entry_total=1.0 value_sum=1 value_total=3732.0 method=text                          |
| checksum | 0001079738-12-000003 | entry count off by >2, unexplained          | rows=61 entry_total=1.0 value_sum=168090 value_total=168090.0 method=text                  |
| checksum | 0000918504-12-000003 | entry count off by >2, unexplained          | rows=101 entry_total=1.0 value_sum=236634 value_total=nan method=text                      |
| checksum | 0001193125-12-177684 | entry count off by <=2                      | rows=743 entry_total=744.0 value_sum=1749091 value_total=1749094.0 method=text             |
| checksum | 0000893838-12-000031 | entry count off by >2, unexplained          | rows=2855 entry_total=7.0 value_sum=1922130 value_total=9302999.0 method=text              |
| checksum | 0000893838-12-000027 | no rows parsed                              | rows=0 entry_total=3.0 value_sum=0 value_total=0.0 method=text                             |
| checksum | 0001509445-12-000002 | entry total counts distinct CUSIPs not rows | rows=20 entry_total=21.0 value_sum=353727 value_total=318886000.0 method=text              |
| checksum | 0001121477-12-000002 | entry total counts distinct CUSIPs not rows | rows=215 entry_total=216.0 value_sum=129482 value_total=129855.0 method=text               |
| checksum | 0001174248-12-000002 | entry total counts distinct CUSIPs not rows | rows=198 entry_total=200.0 value_sum=355148 value_total=354026.0 method=text               |
| checksum | 0001085146-12-000533 | entry off by <=2 and value off >1%          | rows=61 entry_total=63.0 value_sum=5956068 value_total=5685966.0 method=text               |
| checksum | 0001228242-12-000007 | no rows parsed                              | rows=0 entry_total=616.0 value_sum=0 value_total=nan method=text                           |
| checksum | 0001193125-12-235016 | value off >1%, unexplained                  | rows=131 entry_total=131.0 value_sum=13018935 value_total=7765604.0 method=text            |
| checksum | 0000872162-12-000005 | no rows parsed                              | rows=0 entry_total=87.0 value_sum=0 value_total=486821.0 method=text                       |
| checksum | 0001144204-12-027116 | entry count off by >2, unexplained          | rows=1872 entry_total=1896.0 value_sum=284814922 value_total=45021198.0 method=text        |
| checksum | 0001047339-12-000003 | entry count off by >2, unexplained          | rows=133 entry_total=141.0 value_sum=208442 value_total=209567.0 method=text               |
| checksum | 0001106544-12-000004 | value scale x1000 (dollars vs thousands)    | rows=47 entry_total=47.0 value_sum=176996 value_total=177265921.0 method=text              |
| checksum | 0001534866-12-000002 | entry total counts distinct CUSIPs not rows | rows=515 entry_total=296.0 value_sum=4525893 value_total=4525893.0 method=text             |
| checksum | 0001089212-12-000005 | value scale x1000 (dollars vs thousands)    | rows=120 entry_total=120.0 value_sum=1330337 value_total=1330332000.0 method=text          |
| checksum | 0000940445-12-000004 | entry total counts distinct CUSIPs not rows | rows=404 entry_total=405.0 value_sum=771898 value_total=776019.0 method=text               |
| checksum | 0001193125-12-234635 | value scale x1000 (dollars vs thousands)    | rows=45 entry_total=46.0 value_sum=4057506884 value_total=4373080.0 method=text            |
| checksum | 0001144204-12-029071 | entry count off by >2, unexplained          | rows=450 entry_total=314383588.0 value_sum=13747420 value_total=13747420.0 method=text     |
| checksum | 0001455125-12-000006 | no rows parsed                              | rows=0 entry_total=354.0 value_sum=0 value_total=101753.0 method=text                      |
| checksum | 0001352764-12-000005 | entry total counts distinct CUSIPs not rows | rows=106 entry_total=107.0 value_sum=780179 value_total=783038.0 method=text               |
| checksum | 0001388142-12-000004 | entry count off by >2, unexplained          | rows=42 entry_total=45.0 value_sum=163664 value_total=175581.0 method=text                 |
| checksum | 0001526411-12-000004 | entry count off by >2, unexplained          | rows=355 entry_total=363.0 value_sum=971485 value_total=971479.0 method=text               |
| checksum | 0001550075-12-000001 | entry total counts distinct CUSIPs not rows | rows=822 entry_total=821.0 value_sum=1695906 value_total=1688548.0 method=text             |
| checksum | 0001352859-12-000003 | value scale x1000 (dollars vs thousands)    | rows=136 entry_total=136.0 value_sum=134930 value_total=134933000.0 method=text            |
| checksum | 0000811393-12-000004 | entry count off by >2, unexplained          | rows=576 entry_total=288.0 value_sum=240664 value_total=120332.0 method=text               |
| checksum | 0000312069-12-000065 | entry count off by >2, unexplained          | rows=14432 entry_total=73621735.0 value_sum=73621735 value_total=14432.0 method=text       |
| checksum | 0001193125-12-233464 | value off >1%, unexplained                  | rows=103 entry_total=103.0 value_sum=447822 value_total=44786865.0 method=text             |
| checksum | 0001409427-12-000004 | entry count off by >2, unexplained          | rows=217 entry_total=220.0 value_sum=791817 value_total=952144.0 method=text               |
| checksum | 0001193125-12-170153 | entry count off by >2, unexplained          | rows=282 entry_total=292.0 value_sum=886825 value_total=937271.0 method=text               |
| checksum | 0000070858-12-000214 | value scale x1000 (dollars vs thousands)    | rows=17027 entry_total=17027.0 value_sum=187771783 value_total=187774352000.0 method=text  |
| checksum | 0000315080-12-000003 | entry count off by >2, unexplained          | rows=435 entry_total=408.0 value_sum=918301 value_total=852552.0 method=text               |
| checksum | 0001483472-12-000003 | entry count off by >2, unexplained          | rows=98 entry_total=105.0 value_sum=97753 value_total=98415.0 method=text                  |
| checksum | 0001204459-12-001102 | entry total counts distinct CUSIPs not rows | rows=240 entry_total=242.0 value_sum=930426 value_total=329425.0 method=text               |
| checksum | 0001398344-12-001850 | no rows parsed                              | rows=0 entry_total=199.0 value_sum=0 value_total=288674.0 method=text                      |
| checksum | 0001510320-12-000003 | entry total counts distinct CUSIPs not rows | rows=254 entry_total=253.0 value_sum=299441 value_total=299440.0 method=text               |
| checksum | 0001317829-12-000004 | entry total counts distinct CUSIPs not rows | rows=45 entry_total=46.0 value_sum=9226 value_total=9322.0 method=text                     |
| checksum | 0001047469-12-005935 | entry count off by >2, unexplained          | rows=329 entry_total=317.0 value_sum=589743 value_total=551539.0 method=text               |
| checksum | 0001140361-12-025020 | entry count off by <=2                      | rows=786 entry_total=788.0 value_sum=25553478 value_total=25550402.0 method=text           |
| checksum | 0001019687-12-001856 | entry count off by >2, unexplained          | rows=71 entry_total=74.0 value_sum=245850 value_total=243599.0 method=text                 |
| checksum | 0000860828-12-000002 | value scale x1000 (dollars vs thousands)    | rows=97 entry_total=97.0 value_sum=284351516 value_total=284352.0 method=text              |
| checksum | 0000934729-12-000033 | entry total counts distinct CUSIPs not rows | rows=12965 entry_total=3506.0 value_sum=58422514 value_total=58422514.0 method=text        |
| checksum | 0000950156-12-000024 | entry off by <=2 and value within 1%        | rows=61 entry_total=63.0 value_sum=87110 value_total=87434.0 method=text                   |
| checksum | 0001193125-12-223631 | entry count off by >2, unexplained          | rows=1155 entry_total=1179.0 value_sum=6333402 value_total=6648699.0 method=text           |
| checksum | 0001140361-12-021346 | no rows parsed                              | rows=0 entry_total=0.0 value_sum=0 value_total=47742072.0 method=text                      |
| checksum | 0001074273-12-000002 | value scale x1000 (dollars vs thousands)    | rows=59 entry_total=59.0 value_sum=175375446 value_total=175375.0 method=text              |
| checksum | 0001193125-12-160376 | entry count off by >2, unexplained          | rows=705 entry_total=709.0 value_sum=817451 value_total=817451.0 method=text               |
| checksum | 0000945621-12-000129 | value scale x1000 (dollars vs thousands)    | rows=1494 entry_total=1494.0 value_sum=2411467 value_total=2411467000.0 method=text        |
| checksum | 0001140361-12-025113 | entry count off by >2, unexplained          | rows=295 entry_total=299.0 value_sum=431854 value_total=441169.0 method=text               |
| checksum | 0000019475-12-000002 | value scale x1000 (dollars vs thousands)    | rows=89 entry_total=89.0 value_sum=571104 value_total=571104000.0 method=text              |
| checksum | 0001276460-12-000003 | entry count off by >2, unexplained          | rows=88 entry_total=93.0 value_sum=678281 value_total=680726.0 method=text                 |
| checksum | 0001455176-12-000004 | entry count off by >2, unexplained          | rows=103 entry_total=87.0 value_sum=284357 value_total=284357.0 method=text                |
| checksum | 0001085146-12-000780 | value off >1%, unexplained                  | rows=268 entry_total=268.0 value_sum=552547 value_total=508547.0 method=text               |
| checksum | 0001163648-12-000009 | value within 1% (rounding)                  | rows=305 entry_total=305.0 value_sum=10236177 value_total=10212847.0 method=text           |
| checksum | 0001421224-12-000002 | value off >1%, unexplained                  | rows=356 entry_total=356.0 value_sum=22987833 value_total=29723475.0 method=text           |
| checksum | 0001080628-12-000002 | value scale x1000 (dollars vs thousands)    | rows=134 entry_total=134.0 value_sum=506888 value_total=506953000.0 method=text            |
| checksum | 0001398344-12-001651 | entry count off by >2, unexplained          | rows=175 entry_total=194.0 value_sum=185107 value_total=201840.0 method=text               |
| checksum | 0001492166-12-000011 | value off >1%, unexplained                  | rows=300 entry_total=300.0 value_sum=288965 value_total=248965.0 method=text               |
| checksum | 0001483499-12-000003 | entry count off by >2, unexplained          | rows=182 entry_total=178.0 value_sum=427569 value_total=429964.0 method=text               |
| checksum | 0001340807-12-000015 | value off >1%, unexplained                  | rows=74 entry_total=74.0 value_sum=22471999 value_total=427836.0 method=text               |
| checksum | 0001193125-12-162010 | value scale x1000 (dollars vs thousands)    | rows=154 entry_total=154.0 value_sum=417721 value_total=417798716.0 method=text            |
| checksum | 0001141455-12-000003 | value scale x1000 (dollars vs thousands)    | rows=102 entry_total=100.0 value_sum=329030 value_total=328002000.0 method=text            |
| checksum | 0001086364-12-002435 | value within 1% (rounding)                  | rows=9692 entry_total=9692.0 value_sum=58663863 value_total=58749608.0 method=text         |
| checksum | 0001086364-12-002420 | value within 1% (rounding)                  | rows=3498 entry_total=3498.0 value_sum=39702669 value_total=39635961.0 method=text         |
| checksum | 0001193125-12-235050 | entry total counts distinct CUSIPs not rows | rows=24 entry_total=25.0 value_sum=6766102 value_total=9784649.0 method=text               |
| checksum | 0000909012-12-000218 | entry count off by >2, unexplained          | rows=341 entry_total=395.0 value_sum=179579421 value_total=179973532.0 method=text         |
| checksum | 0001080071-12-000005 | value within 1% (rounding)                  | rows=126 entry_total=126.0 value_sum=139974 value_total=139052.0 method=text               |
| checksum | 0001140804-12-000011 | entry count off by >2, unexplained          | rows=414 entry_total=261921281.0 value_sum=8385544787 value_total=8385823354.0 method=text |
| checksum | 0001015247-12-000003 | entry count off by >2, unexplained          | rows=308 entry_total=283.0 value_sum=130545275 value_total=417590.0 method=text            |
| checksum | 0000898432-12-000625 | entry total counts distinct CUSIPs not rows | rows=10 entry_total=11.0 value_sum=69316 value_total=70233.0 method=text                   |
| checksum | 0001548680-12-000002 | entry off by <=2 and value off >1%          | rows=39 entry_total=37.0 value_sum=141478 value_total=56805.0 method=html                  |
| checksum | 0001166880-12-000004 | entry count off by >2, unexplained          | rows=79 entry_total=179.0 value_sum=107966 value_total=205154.0 method=text                |
| checksum | 0000891118-12-000005 | value scale x1000 (dollars vs thousands)    | rows=35 entry_total=35.0 value_sum=391971000 value_total=391991.0 method=text              |
| checksum | 0001144204-12-019650 | value scale x1000 (dollars vs thousands)    | rows=78 entry_total=78.0 value_sum=260712921 value_total=260712.0 method=text              |
| checksum | 0001166564-12-000004 | value off >1%, unexplained                  | rows=36 entry_total=36.0 value_sum=24879934 value_total=504240.0 method=text               |
| checksum | 0001193125-12-234902 | entry count off by >2, unexplained          | rows=560 entry_total=567.0 value_sum=5221475 value_total=5244155.0 method=text             |
| checksum | 0001285973-12-000004 | value off >1%, unexplained                  | rows=50 entry_total=50.0 value_sum=133604 value_total=130025.0 method=text                 |
| checksum | 0001085146-12-000648 | entry total counts distinct CUSIPs not rows | rows=180 entry_total=181.0 value_sum=470606 value_total=470606.0 method=text               |
| checksum | 0001388549-12-000004 | entry count off by >2, unexplained          | rows=837 entry_total=1936.0 value_sum=171876615 value_total=237713.0 method=text           |
| checksum | 0001542166-12-000002 | value scale x1000 (dollars vs thousands)    | rows=34 entry_total=34.0 value_sum=146786 value_total=146801296.0 method=text              |
| checksum | 0001348886-12-000005 | entry total counts distinct CUSIPs not rows | rows=41 entry_total=40.0 value_sum=246433 value_total=229917.0 method=text                 |
| checksum | 0000909518-12-000178 | value scale x1000 (dollars vs thousands)    | rows=3 entry_total=3.0 value_sum=323854370 value_total=323854.0 method=text                |
| checksum | 0001434845-12-000002 | value within 1% (rounding)                  | rows=71 entry_total=71.0 value_sum=143035063 value_total=143421709.0 method=text           |
| checksum | 0001510870-12-000002 | value off >1%, unexplained                  | rows=55 entry_total=55.0 value_sum=129548 value_total=36048.0 method=text                  |
| checksum | 0001162044-12-000462 | entry count off by >2, unexplained          | rows=223 entry_total=226.0 value_sum=93369 value_total=93368.0 method=text                 |
| checksum | 0001162044-12-000470 | entry count off by >2, unexplained          | rows=247 entry_total=250.0 value_sum=103828 value_total=103826.0 method=text               |
| checksum | 0001419186-12-000006 | entry total counts distinct CUSIPs not rows | rows=791 entry_total=792.0 value_sum=1275767 value_total=1276267.0 method=text             |
| checksum | 0001193125-12-222189 | entry count off by >2, unexplained          | rows=90 entry_total=102.0 value_sum=266983 value_total=266347.0 method=text                |
| checksum | 0000902664-12-000790 | value off >1%, unexplained                  | rows=31 entry_total=31.0 value_sum=274883 value_total=1284108.0 method=text                |
| checksum | 0001140361-12-026031 | entry count off by >2, unexplained          | rows=12 entry_total=22.0 value_sum=4345347 value_total=204678.0 method=text                |
| checksum | 0001381066-12-000003 | value within 1% (rounding)                  | rows=106 entry_total=106.0 value_sum=239417 value_total=238786.0 method=text               |
| checksum | 0001454968-12-000004 | entry count off by <=2                      | rows=168 entry_total=169.0 value_sum=323959 value_total=323959.0 method=text               |
| checksum | 0001453620-12-000004 | entry total counts distinct CUSIPs not rows | rows=102 entry_total=101.0 value_sum=257433 value_total=257428.0 method=text               |
| checksum | 0001333978-12-000005 | entry total counts distinct CUSIPs not rows | rows=1683 entry_total=1684.0 value_sum=4464603 value_total=4465734.0 method=text           |
| checksum | 0001455005-12-000002 | entry count off by >2, unexplained          | rows=68 entry_total=32.0 value_sum=222008 value_total=205864.0 method=text                 |
| checksum | 0000890163-12-000017 | entry count off by >2, unexplained          | rows=254 entry_total=273.0 value_sum=264107 value_total=256023.0 method=text               |
| checksum | 0001379495-12-000005 | value within 1% (rounding)                  | rows=41 entry_total=41.0 value_sum=261720 value_total=261170.0 method=text                 |
| checksum | 0001085146-12-000568 | value off >1%, unexplained                  | rows=1880 entry_total=1880.0 value_sum=610693 value_total=576890.0 method=text             |
| checksum | 0001317172-12-000032 | value scale x1000 (dollars vs thousands)    | rows=7 entry_total=7.0 value_sum=63892 value_total=63896135.0 method=text                  |
| checksum | 0001163744-12-000005 | entry total counts distinct CUSIPs not rows | rows=124 entry_total=123.0 value_sum=722417 value_total=722417.0 method=text               |
| checksum | 0001474208-12-000004 | entry count off by >2, unexplained          | rows=371 entry_total=381.0 value_sum=940177 value_total=954292.0 method=text               |
| checksum | 0001510669-12-000005 | entry off by <=2 and value within 1%        | rows=57 entry_total=58.0 value_sum=1456957 value_total=1462525.0 method=text               |
| checksum | 0001387131-12-001583 | entry total counts distinct CUSIPs not rows | rows=31 entry_total=32.0 value_sum=863217 value_total=865469.0 method=text                 |
| checksum | 0001193125-12-217266 | value scale x1000 (dollars vs thousands)    | rows=126 entry_total=126.0 value_sum=7015216 value_total=7015.0 method=text                |
| checksum | 0001422219-12-000004 | entry total counts distinct CUSIPs not rows | rows=128 entry_total=129.0 value_sum=851849 value_total=851894.0 method=text               |
| checksum | 0001406995-12-000004 | entry count off by >2, unexplained          | rows=185 entry_total=188.0 value_sum=170172 value_total=174032.0 method=text               |
| checksum | 0001323119-12-000002 | value scale x1000 (dollars vs thousands)    | rows=206 entry_total=229.0 value_sum=745756 value_total=702135000.0 method=text            |
| checksum | 0001058217-12-000007 | value scale x1000 (dollars vs thousands)    | rows=44 entry_total=43.0 value_sum=22071 value_total=21845000.0 method=text                |
| checksum | 0001193125-12-227272 | value scale x1000 (dollars vs thousands)    | rows=323 entry_total=323.0 value_sum=23126371 value_total=23126355000.0 method=text        |
| checksum | 0001193125-12-217682 | value off >1%, unexplained                  | rows=5606 entry_total=5606.0 value_sum=273014038 value_total=11951990.0 method=text        |
| checksum | 0001085146-12-000736 | entry count off by >2, unexplained          | rows=1974 entry_total=1981.0 value_sum=6939256 value_total=6955792.0 method=text           |
| checksum | 0000767684-12-000004 | value scale x1000 (dollars vs thousands)    | rows=134 entry_total=134.0 value_sum=609199 value_total=609199000.0 method=text            |
| checksum | 0000893738-12-000002 | value scale x1000 (dollars vs thousands)    | rows=55 entry_total=55.0 value_sum=124238 value_total=124238000.0 method=text              |
| checksum | 0001145935-12-000005 | entry count off by >2, unexplained          | rows=129 entry_total=311.0 value_sum=909090 value_total=2557606.0 method=text              |
| checksum | 0001080107-12-000003 | value scale x1000 (dollars vs thousands)    | rows=3875 entry_total=3875.0 value_sum=1852248 value_total=1852248000.0 method=text        |
| checksum | 0001140771-12-000004 | value scale x1000 (dollars vs thousands)    | rows=690 entry_total=690.0 value_sum=667916 value_total=667916000.0 method=text            |
| checksum | 0001036325-12-000069 | value off >1%, unexplained                  | rows=278 entry_total=278.0 value_sum=48125846 value_total=48.0 method=text                 |
| checksum | 0001085146-12-000677 | entry total counts distinct CUSIPs not rows | rows=155 entry_total=113.0 value_sum=684407 value_total=684407.0 method=text               |
| checksum | 0000936936-12-000002 | entry count off by >2, unexplained          | rows=96 entry_total=82.0 value_sum=167179 value_total=137686000.0 method=text              |
| checksum | 0001193125-12-224194 | value scale x1000 (dollars vs thousands)    | rows=79 entry_total=86.0 value_sum=3825752 value_total=3825752000.0 method=text            |
| checksum | 0000920112-12-000039 | entry count off by >2, unexplained          | rows=468 entry_total=334.0 value_sum=280057057 value_total=282162155.0 method=text         |
| checksum | 0000883511-12-000002 | entry count off by >2, unexplained          | rows=30 entry_total=1.0 value_sum=378886 value_total=nan method=text                       |
| checksum | 0000938077-12-000006 | value off >1%, unexplained                  | rows=410 entry_total=410.0 value_sum=18118796 value_total=186348.0 method=text             |
| checksum | 0000814375-12-000038 | value off >1%, unexplained                  | rows=97 entry_total=97.0 value_sum=4477047 value_total=3439.0 method=text                  |
| checksum | 0001110443-12-000007 | entry count off by >2, unexplained          | rows=129 entry_total=154.0 value_sum=13430222398 value_total=98409.0 method=text           |
| checksum | 0001193125-12-228709 | entry total counts distinct CUSIPs not rows | rows=3 entry_total=4.0 value_sum=405 value_total=741213.0 method=text                      |
| checksum | 0000831001-12-000151 | value scale x1000 (dollars vs thousands)    | rows=13100 entry_total=13100.0 value_sum=107601492 value_total=107601139041.0 method=text  |
| checksum | 0001144204-12-021231 | value scale x1000 (dollars vs thousands)    | rows=28 entry_total=28.0 value_sum=164295984 value_total=164296.0 method=text              |
| checksum | 0001144204-12-028751 | value scale x1000 (dollars vs thousands)    | rows=31 entry_total=31.0 value_sum=209246916 value_total=209247.0 method=text              |
| checksum | 0001384042-12-000004 | entry total counts distinct CUSIPs not rows | rows=660 entry_total=184.0 value_sum=271128 value_total=271717.0 method=text               |
| checksum | 0001308527-12-000002 | value scale x1000 (dollars vs thousands)    | rows=183 entry_total=168.0 value_sum=756926 value_total=758801788.0 method=text            |
| checksum | 0001047469-12-005706 | entry total counts distinct CUSIPs not rows | rows=87 entry_total=65.0 value_sum=69811 value_total=69810.0 method=text                   |
| checksum | 0001435346-12-000006 | entry total counts distinct CUSIPs not rows | rows=139 entry_total=138.0 value_sum=839900 value_total=839892.0 method=text               |
| checksum | 0001344422-12-000004 | entry count off by <=2                      | rows=113 entry_total=114.0 value_sum=136387 value_total=136419.0 method=text               |
| checksum | 0000790502-12-000033 | value scale x1000 (dollars vs thousands)    | rows=533 entry_total=533.0 value_sum=13394008 value_total=13394270287.0 method=text        |
| checksum | 0000945631-12-000006 | value scale x1000 (dollars vs thousands)    | rows=53 entry_total=53.0 value_sum=12122212 value_total=12122213000.0 method=text          |
| checksum | 0001086521-12-000006 | entry count off by >2, unexplained          | rows=1521 entry_total=1872.0 value_sum=10075150069670 value_total=6209245.0 method=text    |
| checksum | 0000354204-12-001346 | value off >1%, unexplained                  | rows=3689 entry_total=3689.0 value_sum=86224871 value_total=88316829.0 method=text         |
| checksum | 0001140361-12-025357 | entry off by <=2 and value off >1%          | rows=132 entry_total=134.0 value_sum=4589428 value_total=4456299.0 method=text             |
| checksum | 0001461133-12-000002 | entry count off by >2, unexplained          | rows=89 entry_total=345.0 value_sum=21036 value_total=80009.0 method=text                  |
| checksum | 0001479844-12-000003 | entry count off by >2, unexplained          | rows=801 entry_total=806.0 value_sum=795262 value_total=797993.0 method=text               |
| checksum | 0001193125-12-183289 | value scale x1000 (dollars vs thousands)    | rows=350 entry_total=350.0 value_sum=2973437942 value_total=2973438.0 method=text          |
| checksum | 0001260824-12-000004 | entry total counts distinct CUSIPs not rows | rows=123 entry_total=122.0 value_sum=514309 value_total=15209437.0 method=text             |
| checksum | 0001082970-12-000004 | value scale x1000 (dollars vs thousands)    | rows=500 entry_total=500.0 value_sum=3584210 value_total=3584210000.0 method=text          |
| checksum | 0001013538-12-000004 | value off >1%, unexplained                  | rows=56 entry_total=56.0 value_sum=1229993 value_total=122999.0 method=text                |
| checksum | 0001386088-12-000002 | no rows parsed                              | rows=0 entry_total=36.0 value_sum=0 value_total=3283291.0 method=text                      |
| checksum | 0001313926-12-000003 | value off >1%, unexplained                  | rows=15 entry_total=15.0 value_sum=2015345 value_total=2321065000.0 method=text            |