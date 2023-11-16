import csv
import pandas as pd
import gzip
from typing import Dict

def read_gmt(path):
    with open(path) as read_file:
        return [(row[0], row[1], set(row[2:])) for row in csv.reader(read_file, delimiter='\t') if row]

def parse_description(description):
    return dict(item.split(': ', 1) for item in description.split('; ') if ': ' in item)

def process_pathwaycommons_data(path: str, symbol_to_entrez: Dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            'identifier': url.rsplit('/', 1)[-1],
            'name': parse_description(description).get('name'),
            'url': url,
            'genes': {symbol_to_entrez[gene] for gene in genes if gene in symbol_to_entrez}
        }
        for url, description, genes in read_gmt(path) 
        if {gene for gene in genes if gene in symbol_to_entrez}
    ])

def process_wikipathways_data(gmt_data, human_genes):
    wikipath_df = pd.DataFrame(gmt_data, columns=['name', 'description', 'genes'])
    wikipath_df['name'] = wikipath_df['name'].str.split('%').str[0]
    wikipath_df['genes'] = wikipath_df['genes'].apply(lambda genes: genes & human_genes)
    return wikipath_df[wikipath_df['genes'].astype(bool)]

def create_combined_df(pc_df, wikipath_df):
    wikipath_df = wikipath_df.assign(
        identifier = wikipath_df['description'].str.rsplit('/', n=1).str[-1],
        url = wikipath_df['description']
    )
    combined_df = pd.concat([wikipath_df, pc_df], ignore_index=True).drop_duplicates('genes')
    combined_df['n_genes'] = combined_df['genes'].apply(len)
    return combined_df[['identifier', 'name', 'url', 'n_genes', 'genes']].sort_values('identifier')

def write_to_tsv(dataframe, filepath):
    dataframe['genes'] = dataframe['genes'].apply(lambda x: '|'.join(map(str, sorted(x))))
    dataframe.to_csv(filepath, index=False, sep='\t')

def main():
    gene_info_path = 'data/input/Homo_sapiens.gene_info.gz'
    with gzip.open(gene_info_path, 'rt') as file:
        gene_df = pd.read_csv(file, delimiter='\t')

    human_genes = set(gene_df['GeneID'].astype(str))
    symbol_to_entrez = dict(zip(gene_df['Symbol'], gene_df['GeneID'].astype(str)))

    pc_df = process_pathwaycommons_data("data/input/PathwayCommons12.All.hgnc.gmt", symbol_to_entrez)
    gmt_data = read_gmt('data/input/wikipathways-Homo_sapiens.gmt')
    wikipath_df = process_wikipathways_data(gmt_data, human_genes)

    pathway_df = create_combined_df(pc_df, wikipath_df)
    write_to_tsv(pathway_df, 'data/output/pathways.tsv')

if __name__ == "__main__":
    main()
