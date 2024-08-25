import requests
import xml.etree.ElementTree as ET
import csv
from datetime import datetime, timedelta
import time
#AND ("GIP"[Abstract] OR "SGLT2"[Abstract] OR "GLP-1"[Abstract] OR "treatment"[Abstract]))
# To get only articles published in the last 7 days
def fetch_recent_pmids(max_results):
    pmids = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    params = {
        'db': 'pubmed',
        'term': f'("cancer"[Abstract] OR "tumor"[Abstract] OR "diabetes"[Abstract] AND ("{start_date.strftime("%Y/%m/%d")}"[Date - Publication] : "{end_date.strftime("%Y/%m/%d")}"[Date - Publication])',
        'retmax': max_results,
        'usehistory': 'n',
        'datetype': 'pdat',
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            pmids.extend([id_elem.text for id_elem in root.findall('.//IdList/Id')])
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
    else:
        print(f"Failed to fetch data: {response.status_code}")
    return pmids


def fetch_article_details_with_efetch(pmids):
    articles_info = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    for pmid in pmids:
        time.sleep(1/3)
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml',
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
                for article in root.findall('.//PubmedArticle'):
                    article_id_list = article.find('.//ArticleIdList')
                    pmcid = next((id_elem.text for id_elem in article_id_list.findall(".//ArticleId[@IdType='pmc']")), None)

                    publication_types = [pt.text.lower() for pt in article.findall(".//PublicationTypeList/PublicationType")]
                    unwanted_types = ['review', 'published erratum', 'retraction of publication']
                    if any(t in publication_types for t in unwanted_types):
                        continue

                    title = article.find('.//ArticleTitle').text
                    abstract_texts = article.findall('.//Abstract/AbstractText')
                    abstract = " ".join([text.text for text in abstract_texts if text.text is not None])
                    pub_date_element = article.find('.//PubDate')
                    year = pub_date_element.find('Year').text if pub_date_element.find('Year') is not None else 'N/A'
                    month = pub_date_element.find('Month').text if pub_date_element.find('Month') is not None else 'N/A'
                    day = pub_date_element.find('Day').text if pub_date_element.find('Day') is not None else 'N/A'
                    pubdate = f"{year}-{month}-{day}" if year != 'N/A' else 'N/A'
                    doi = next((id_elem.text for id_elem in article_id_list.findall(".//ArticleId[@IdType='doi']")), None)
                    online_pub_element = article.find('.//ArticleDate')
                    online_pub = None
                    if online_pub_element is not None and online_pub_element.get('DateType') == 'Electronic':
                        year = online_pub_element.find('Year').text if online_pub_element.find('Year') is not None else None
                        month = online_pub_element.find('Month').text if online_pub_element.find('Month') is not None else None
                        day = online_pub_element.find('Day').text if online_pub_element.find('Day') is not None else None
                        online_pub = f"{year}-{month}-{day}" if year is not None else None
                    online_pub = pubdate if online_pub is None else online_pub
                    journal = article.find('.//Journal/Title').text if article.find('.//Journal/Title') is not None else 'N/A'
                    authors = '; '.join([f"{author.find('LastName').text}, {author.find('ForeName').text}" for author in article.findall('.//Author') if author.find('LastName') is not None and author.find('ForeName') is not None])
                    keywords = '; '.join([kw.text for kw in article.findall(".//KeywordList/Keyword")])
                    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ''
                    pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    affiliations = []
                    for author in article.findall('.//Author'):
                        affiliation_element = author.find('.//Affiliation')
                        affiliation = affiliation_element.text.strip() if affiliation_element is not None else None
                        if affiliation:  # Check if affiliation is not None before appending
                            affiliations.append(affiliation)
                    affiliation = '; '.join(affiliations) if affiliations else None  # Use None if no affiliations found
                    articles_info.append({
                        'pmid': pmid,
                        'pmcid': pmcid,
                        'doi': doi,
                        'title': title,
                        'abstract': abstract,
                        'pubdate': pubdate,
                        'online_pub': online_pub,
                        'journal': journal,
                        'authors': authors,
                        'research_institute': affiliation,
                        'keywords': keywords,
                        'publication_type': '; '.join(publication_types),
                        'url': url,
                        'pmid_url': pmid_url,
                    })
            except ET.ParseError as e:
                print(f"Error parsing XML for PMID {pmid}: {e}")
        else:
            print(f"Failed to fetch details for PMID {pmid}")

    return articles_info

def save_articles_to_csv(articles, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['pmid', 'pmcid', 'doi', 'pmid_url', 'title', 'abstract', 'pubdate', 'online_pub', 'journal', 'authors', 'research_institute', 'keywords', 'publication_type', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for article in articles:
            writer.writerow(article)

max_results = 1500
pmids = fetch_recent_pmids(max_results)
articles = fetch_article_details_with_efetch(pmids)
output_path = 'pubmed_batch_articles.csv'
save_articles_to_csv(articles, output_path)

print("Article details have been saved to 'pubmed_batch_articles.csv'.")
