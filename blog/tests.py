import json

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Post, Tag


@override_settings(OPENCLAW_BLOG_API_TOKEN='test-openclaw-token')
class OpenClawPublishPostTests(TestCase):
	def test_creates_published_post_with_tags(self):
		response = self.client.post(
			reverse('openclaw_publish_post'),
			data=json.dumps(
				{
					'title': 'New OpenClaw Article',
					'description': 'API created post',
					'content': '# Markdown body',
					'language': 'en',
					'slug': 'new-openclaw-article',
					'tags': ['OpenClaw', {'name_ru': 'Автоматизация', 'name_en': 'Automation'}],
				}
			),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer test-openclaw-token',
		)

		self.assertEqual(response.status_code, 201)
		payload = response.json()

		post = Post.objects.get(pk=payload['id'])
		self.assertEqual(post.slug, 'new-openclaw-article')
		self.assertEqual(post.language, 'en')
		self.assertIsNotNone(post.published_date)
		self.assertEqual(post.tags.count(), 2)
		self.assertTrue(Tag.objects.filter(slug='openclaw').exists())

	def test_rejects_invalid_token(self):
		response = self.client.post(
			reverse('openclaw_publish_post'),
			data=json.dumps({'title': 'Denied', 'content': 'No auth'}),
			content_type='application/json',
			HTTP_X_API_KEY='wrong-token',
		)

		self.assertEqual(response.status_code, 401)

	def test_rejects_invalid_payload(self):
		response = self.client.post(
			reverse('openclaw_publish_post'),
			data=json.dumps({'title': '', 'content': ''}),
			content_type='application/json',
			HTTP_X_API_KEY='test-openclaw-token',
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Post.objects.count(), 0)
