import copy, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import job_search_automation as app
from schedule_gate import should_run

NOW=datetime(2026,11,11,7,17,tzinfo=timezone.utc)
def job(**kwargs):
    j=dict(title='Senior Content Designer',company='Example',location='Spain - Remote',description='Own content strategy and content governance. Write clear UX copy and manage content workflows. Partner with product teams on localization and accessibility for digital health.',url='https://example.com/jobs/1234',remote=True,employment='Contract',salary='Not published',published='',source='Example',source_kind='greenhouse')
    j.update(kwargs); return j

class Relevance(unittest.TestCase):
    def test_senior_spain(self): self.assertIsNotNone(app.evaluate(job(),NOW))
    def test_us_citizenship_does_not_override_location(self): self.assertIsNone(app.evaluate(job(location='United States - Remote'),NOW))
    def test_barcelona_hybrid(self): self.assertIsNotNone(app.evaluate(job(location='Barcelona',remote=False),NOW))
    def test_madrid_office_excluded(self): self.assertIsNone(app.evaluate(job(location='Madrid',remote=False),NOW))
    def test_spain_office_excluded(self): self.assertIsNone(app.evaluate(job(location='Spain',remote=False),NOW))
    def test_europe_office_excluded(self): self.assertIsNone(app.evaluate(job(location='Europe',remote=False),NOW))
    def test_remote_unknown_excluded(self): self.assertIsNone(app.evaluate(job(location='Remote'),NOW))
    def test_region_label_is_conditional(self): self.assertTrue(app.evaluate(job(location='EMEA - Remote'),NOW)['regional'])
    def test_us_only_overrides_worldwide(self): self.assertIsNone(app.evaluate(job(location='Worldwide',description=job()['description']+' Applicants must be based in the United States.'),NOW))
    def test_intern_excluded(self): self.assertIsNone(app.evaluate(job(title='Content Design Intern'),NOW))
    def test_engineering_excluded_even_with_keywords(self): self.assertIsNone(app.evaluate(job(title='Senior Software Engineer'),NOW))
    def test_technical_program_manager_excluded(self): self.assertIsNone(app.evaluate(job(title='Technical Program Manager'),NOW))
    def test_generic_product_manager_excluded(self): self.assertIsNone(app.evaluate(job(title='Product Manager'),NOW))
    def test_adjacent_role_uses_description(self): self.assertIsNotNone(app.evaluate(job(title='Brand Experience Lead'),NOW))
    def test_unrelated_keyword_is_not_enough(self): self.assertIsNone(app.evaluate(job(description='A content management software company looking for an employee.'),NOW))
    def test_devdocs_excluded(self): self.assertIsNone(app.evaluate(job(title='Technical Writer',description=job()['description']+' Write API reference and SDK code samples.'),NOW))
    def test_paid_access_excluded(self): self.assertIsNone(app.evaluate(job(description=job()['description']+' Accessing writing tasks may require payment.'),NOW))
    def test_contract_priority(self): self.assertGreater(app.evaluate(job(),NOW)['score'],app.evaluate(job(employment='Full-time'),NOW)['score'])
    def test_missing_salary_allowed(self): self.assertEqual(app.evaluate(job(),NOW)['salary'],'Not published')
    def test_old_jobs_excluded(self): self.assertIsNone(app.evaluate(job(published='2025-01-01T00:00:00Z'),NOW))
    def test_dedupe_cross_source(self):
        a=app.evaluate(job(),NOW); b=app.evaluate(job(url='https://different.com/job/123'),NOW)
        self.assertEqual(len(app.dedupe([a,b])),1)
    def test_non_job_urls(self):
        for u in ['javascript:alert(1)','https://example.com/jobs','https://example.com/search/content','https://example.com/']:
            self.assertFalse(app.safe_job_url(u))
    def test_tracking_removed(self): self.assertEqual(app.canonical('https://example.com/jobs/1?utm_source=x#top'),'https://example.com/jobs/1')

class Adapters(unittest.TestCase):
    def test_greenhouse_html_decoding(self):
        row={'title':'Senior Content Designer','location':{'name':'Spain - Remote'},'absolute_url':'https://example.com/jobs/123','content':'&lt;p&gt;Write &amp;amp; edit&lt;/p&gt;'}
        j=app.normalize({'kind':'greenhouse','name':'Example'},{'jobs':[row]})[0]
        self.assertIn('Write & edit',j['description']); self.assertNotIn('<p>',j['description'])
    def test_malformed_source_is_failure(self):
        with self.assertRaises(ValueError): app.normalize({'kind':'greenhouse','name':'x'},{'error':'oops'})
    def test_ashby_multiple_locations(self):
        r={'title':'Senior Content Designer','location':'London','secondaryLocations':[{'location':'Spain'}],'isRemote':True,'descriptionPlain':job()['description'],'jobUrl':'https://jobs.ashbyhq.com/a/123','employmentType':'FullTime'}
        self.assertIsNotNone(app.evaluate(app.normalize({'kind':'ashby','name':'x'},{'jobs':[r]})[0],NOW))

class Recovery(unittest.TestCase):
    def sources(self): return [dict(kind='greenhouse',name='A',url='https://example.com/a'),dict(kind='greenhouse',name='B',url='https://example.com/b')]
    def test_network_failure_preserves_report(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'docs'; out.mkdir(); (out/'index.html').write_text('previous successful report')
            with patch.object(app,'fetch',side_effect=OSError('offline')): code=app.run(self.sources(),out,Path(td)/'data',NOW)
            self.assertEqual(code,1); self.assertEqual((out/'index.html').read_text(),'previous successful report')
            self.assertFalse(json.loads((Path(td)/'data/last_attempt.json').read_text())['success'])
    def test_valid_empty_search_publishes_honest_empty_state(self):
        row=dict(title='Software Engineer',location={'name':'Barcelona'},content='Write software',absolute_url='https://example.com/jobs/123')
        with tempfile.TemporaryDirectory() as td,patch.object(app,'fetch',return_value={'jobs':[row]}):
            out=Path(td)/'docs'; code=app.run(self.sources(),out,Path(td)/'data',NOW)
            self.assertEqual(code,0); self.assertIn('No verified matches today',(out/'index.html').read_text())
    def test_closed_posting_excluded(self):
        with patch.object(app,'fetch',return_value=('https://example.com/jobs/123','This job is no longer available. Apply. Senior Content Designer')):
            self.assertIsNone(app.validate_link(job())[0])
    def test_redirect_to_search_excluded(self):
        with patch.object(app,'fetch',return_value=('https://example.com/jobs','Apply')): self.assertIsNone(app.validate_link(job())[0])
    def test_render_escapes_feed_html(self):
        j=app.evaluate(job(title='<img src=x onerror=alert(1)> Senior Content Designer'),NOW); j['first_found']=NOW.isoformat()
        report=dict(completed_at=NOW.isoformat(),jobs=[j],sources_ok=2,sources_total=2,postings_scanned=20,errors=[],source_status=[])
        with tempfile.TemporaryDirectory() as td:
            app.render(report,Path(td)); output=(Path(td)/'index.html').read_text()
            self.assertNotIn('<img src=x',output); self.assertIn('&lt;img',output); self.assertNotIn('{{',output)

class Schedule(unittest.TestCase):
    def test_winter(self): self.assertTrue(should_run('schedule','17 7 * * *',NOW)); self.assertFalse(should_run('schedule','17 6 * * *',NOW))
    def test_summer(self):
        dt=datetime(2026,7,1,6,17,tzinfo=timezone.utc)
        self.assertTrue(should_run('schedule','17 6 * * *',dt)); self.assertFalse(should_run('schedule','17 7 * * *',dt))
    def test_spring_change(self):
        self.assertTrue(should_run('schedule','17 6 * * *',datetime(2026,3,29,6,17,tzinfo=timezone.utc)))
    def test_autumn_change(self):
        self.assertTrue(should_run('schedule','17 7 * * *',datetime(2026,10,25,7,17,tzinfo=timezone.utc)))
    def test_delayed_runner_still_runs(self): self.assertTrue(should_run('schedule','17 7 * * *',datetime(2026,11,11,10,0,tzinfo=timezone.utc)))
    def test_manual_always_runs(self): self.assertTrue(should_run('workflow_dispatch','',NOW))

if __name__=='__main__': unittest.main()

class AdditionalChecks(unittest.TestCase):
    def test_pay_comparison_uses_explicit_currency_and_period(self):
        self.assertEqual(app.pay_preference('EUR 65000–80000 per year'),4)
        self.assertEqual(app.pay_preference('USD 30 per hour'),-4)
        self.assertEqual(app.pay_preference('USD 500 per day'),4)
        self.assertEqual(app.pay_preference('$50-$75 /hour'),0)
        self.assertEqual(app.pay_preference('GBP 70000 per year'),0)
    def test_failed_previous_match_source_preserves_report(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'docs'; out.mkdir(); (out/'index.html').write_text('previous')
            (out/'results.json').write_text(json.dumps({'jobs':[{'source':'A'}]}))
            sources=[dict(kind='greenhouse',name=n,url='https://example.com/'+n) for n in ['A','B','C']]
            payload={'jobs':[{'title':'Engineer','location':{'name':'Barcelona'},'content':'Write software','absolute_url':'https://example.com/jobs/123'}]}
            def mockfetch(url):
                if url.endswith('/A'): raise OSError('offline')
                return payload
            with patch.object(app,'fetch',side_effect=mockfetch): code=app.run(sources,out,Path(td)/'data',NOW)
            self.assertEqual(code,1); self.assertEqual((out/'index.html').read_text(),'previous')
    def test_aggregator_without_direct_apply_is_excluded(self):
        j=job(source_kind='remotive')
        with patch.object(app,'fetch',return_value=(j['url'],'Senior Content Designer <button>Apply</button>')):
            self.assertIsNone(app.validate_link(j)[0])
    def test_aggregator_resolves_and_checks_direct_application(self):
        j=job(source_kind='arbeitnow')
        pages=[(j['url'],'<a href="https://employer.com/jobs/1234">Apply now</a>'),('https://employer.com/jobs/1234','Senior Content Designer. Apply for this job.')]
        with patch.object(app,'fetch',side_effect=pages): result,error=app.validate_link(j)
        self.assertIsNone(error); self.assertEqual(result['url'],'https://employer.com/jobs/1234')

class EmployerEvidence(unittest.TestCase):
    def test_employer_restriction_overrides_aggregator(self):
        j=job(source_kind='employer',from_aggregator=True)
        page='Senior Content Designer. Apply for this job. Location: CA, US'
        with patch.object(app,'fetch',return_value=(j['url'],page)):
            result,error=app.validate_link(j)
        self.assertIsNone(result); self.assertIn('conflicts with Spain',error['error'])
