import tempfile
from PIL import Image
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor


MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    """Return movie detail URL"""
    return reverse("cinema:movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    """Return movie upload image URL"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def create_user(**params):
    """Helper to create a user"""
    return get_user_model().objects.create_user(**params)


def create_admin(**params):
    """Helper to create admin user"""
    return get_user_model().objects.create_superuser(**params)


class PublicMovieApiTests(APITestCase):
    """Test authenticated access to movie API"""

    def setUp(self):
        self.user = create_user(email="user@test.com", password="testpass")
        self.client.force_authenticate(user=self.user)  # <--- додаємо автентифікацію

    def test_list_movies(self):
        """Authenticated user can list movies"""
        Movie.objects.create(title="Movie 1", description="Desc 1", duration=90)
        Movie.objects.create(title="Movie 2", description="Desc 2", duration=100)
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail(self):
        """Authenticated user can retrieve movie detail"""
        movie = Movie.objects.create(title="Movie 1", description="Desc", duration=90)
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)


class PrivateMovieApiTests(APITestCase):
    """Test authenticated movie API access"""

    def setUp(self):
        self.admin_user = create_admin(email="admin@cinema.com", password="adminpass")
        self.user = create_user(email="user@test.com", password="testpass")

    def test_admin_can_create_movie(self):
        """Admin user can create movie"""
        self.client.force_authenticate(user=self.admin_user)
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        payload = {
            "title": "New Movie",
            "description": "Some description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)
        self.assertEqual(Movie.objects.first().title, payload["title"])

    def test_user_cannot_create_movie(self):
        """Non-admin users cannot create movie"""
        self.client.force_authenticate(user=self.user)
        payload = {"title": "Invalid Movie", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_upload_image(self):
        """Admin can upload movie image"""
        self.client.force_authenticate(user=self.admin_user)
        movie = Movie.objects.create(title="Movie Img", description="Desc", duration=100)
        url = upload_image_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(bool(movie.image))

    def test_user_cannot_upload_image(self):
        """Non-admin cannot upload movie image"""
        self.client.force_authenticate(user=self.user)
        movie = Movie.objects.create(title="Movie Img", description="Desc", duration=100)
        url = upload_image_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        """Filter movies by title"""
        self.client.force_authenticate(user=self.user)
        m1 = Movie.objects.create(title="Movie One", description="D1", duration=100)
        m2 = Movie.objects.create(title="Another Movie", description="D2", duration=120)
        res = self.client.get(MOVIES_URL, {"title": "Movie"})
        self.assertEqual(len(res.data), 2)
        res = self.client.get(MOVIES_URL, {"title": "Another"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], m2.title)

    def test_filter_movies_by_genres(self):
        """Filter movies by genres"""
        self.client.force_authenticate(user=self.user)
        g1 = Genre.objects.create(name="Action")
        g2 = Genre.objects.create(name="Comedy")
        m1 = Movie.objects.create(title="M1", description="D1", duration=90)
        m1.genres.add(g1)
        m2 = Movie.objects.create(title="M2", description="D2", duration=120)
        m2.genres.add(g2)
        res = self.client.get(MOVIES_URL, {"genres": f"{g1.id}"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], m1.title)

    def test_filter_movies_by_actors(self):
        """Filter movies by actors"""
        self.client.force_authenticate(user=self.user)
        a1 = Actor.objects.create(first_name="Tom", last_name="Hanks")
        a2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        m1 = Movie.objects.create(title="M1", description="D1", duration=90)
        m1.actors.add(a1)
        m2 = Movie.objects.create(title="M2", description="D2", duration=120)
        m2.actors.add(a2)
        res = self.client.get(MOVIES_URL, {"actors": f"{a1.id}"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], m1.title)
