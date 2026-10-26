import argparse
import build_site
import search_pages
import build_renditions

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-repo',required=True);p.add_argument('--out',required=True);p.add_argument('--revision',required=True);a=p.parse_args()
    build_site.build(a.dataset_repo,a.out,a.revision)
    search_pages.build(a.dataset_repo,a.out)
    build_renditions.build(a.dataset_repo,a.out)
