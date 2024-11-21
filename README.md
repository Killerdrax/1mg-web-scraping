# 1mg-web-scraping

There are 2 files, one is to collect all the links from all medicines page, the other is to collect the data from the links we collected.

I have created using both Selinium (To overcome all the isuues beautiful soup faces) and Beautiful Soup (For faster scraping).
Implemented dynamic pagination, if all the pages are done in letter A, then it moves to letter B.

In selenium, I have created such that it saves the progress in log file and able to start from where we left off and easy to trace any errors encountered. And the data is saved in json file because, the data is much more easily acessible and managable in json compared to csv.

In Beautyful Soup, I have used JSON LD data to get the links from them
