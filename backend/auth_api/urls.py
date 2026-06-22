from django.urls import path

from .views import (
    AvatarUploadView,
    ChangePasswordView,
    EmailLoginView,
    EmailRegisterView,
    ForgotPasswordView,
    GoogleLoginView,
    LogoutView,
    MeView,
    RefreshView,
    ResetPasswordView,
)

urlpatterns = [
    path("google/", GoogleLoginView.as_view(), name="auth-google"),
    path("register/", EmailRegisterView.as_view(), name="auth-register"),
    path("login/", EmailLoginView.as_view(), name="auth-login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("avatar/", AvatarUploadView.as_view(), name="auth-avatar"),
]
