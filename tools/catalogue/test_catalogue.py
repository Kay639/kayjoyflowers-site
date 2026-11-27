"""Publication boundary tests, using synthetic data only."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from build_catalogue import build

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.master={'revision':1,'integration':{'digital_support_confirmed':True,'nz_store_supported':True,'target_countries':['US'],'store_country':'NZ','support_evidence':'Confirmed account configuration'},'items':[{'id':'sample-book','name':'Example book','description':'Example digital book.','status':'available','kind':'digital_book','pricing':{'amount':'33.00','currency':'USD','billing':'one_time'},'detail_url':'https://example.com/book','purchase_url':'https://example.com/buy','image_url':'https://example.com/cover.png','feed':{'status':'eligible','evidence':'Account eligibility confirmed'},'commercial_approval':'approved','business_info':{'include':True,'approval':'pending'}}]}
    def tearDown(self): self.tmp.cleanup()
    def run_build(self,production=True):
        path=self.root/'master.json'; path.write_text(json.dumps(self.master))
        return build(path,self.root/'out',production)
    def test_eligible_book_exports_but_business_info_stays_pending(self):
        result=self.run_build()
        self.assertEqual(result['feed_rows'],1)
        self.assertFalse(result['business_info_approved'])
        with (self.root/'out/products.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(rows[0]['price'],'33.00 USD')
        self.assertEqual(json.loads(rows[0]['target_countries']),['US'])
        self.assertEqual(rows[0]['is_eligible_checkout'],'false')
    def test_unconfirmed_integration_cannot_publish(self):
        self.master['integration']['nz_store_supported']=False
        with self.assertRaisesRegex(ValueError,'Production blocked'):self.run_build()
        self.assertFalse((self.root/'out/products.csv').exists())
    def test_unreviewed_eligibility_cannot_publish(self):
        self.master['items'][0]['feed']['status']='pending_confirmation'
        with self.assertRaisesRegex(ValueError,'no eligible rows'):self.run_build()
    def test_coming_soon_never_enters_feed(self):
        item=copy.deepcopy(self.master['items'][0]); item.update(id='future-experience',name='Future experience',kind='experience',status='coming_soon',pricing=None,purchase_url=None)
        self.master['items'].append(item)
        self.assertEqual(self.run_build()['feed_rows'],1)
        self.assertIn('Coming Soon',(self.root/'out/business_info_FOR_APPROVAL.txt').read_text())
    def test_coming_soon_checkout_rejected(self):
        self.master['items'][0]['status']='coming_soon'
        with self.assertRaisesRegex(ValueError,'Coming Soon'):self.run_build()
    def test_retirement_does_not_publish_empty_snapshot(self):
        self.master['items'][0]['status']='retired'
        with self.assertRaisesRegex(ValueError,'no eligible rows'):self.run_build()
    def test_duplicate_identifiers_rejected(self):
        self.master['items'].append(copy.deepcopy(self.master['items'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate ID'):self.run_build()
    def test_price_change_needs_commercial_authority(self):
        self.master['items'][0]['commercial_approval']='pending'
        with self.assertRaisesRegex(ValueError,'Commercial approval'):self.run_build()
    def test_ineligible_service_excluded(self):
        item=copy.deepcopy(self.master['items'][0]); item.update(id='service',kind='service')
        item['feed']['status']='pending_confirmation';self.master['items'].append(item)
        self.assertEqual(self.run_build()['feed_rows'],1)
    def test_invalid_currency_rejected(self):
        self.master['items'][0]['pricing']['currency']='DOLLARS'
        with self.assertRaisesRegex(ValueError,'currency'):self.run_build()

if __name__=='__main__': unittest.main()
