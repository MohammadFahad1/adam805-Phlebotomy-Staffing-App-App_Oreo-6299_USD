from rest_framework.permissions import BasePermission


class IsApprovedPhlebotomist(BasePermission):
    message = "Access denied. You are not an approved phlebotomist."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser or request.user.role == 'admin':
            return False
        if request.user.role != 'phlebotomist':
            return False
        if not request.user.is_active:
            return False
        if request.user.suspended:
            self.message = "Access denied. Your account has been suspended."
            return False
        try:
            return request.user.phlebotomist_profile.approved is True
        except Exception:
            return False

    def has_object_permission(self, request, view, obj):
        # The object must belong to the requesting phlebotomist.
        # Supports objects owned directly via a 'phlebotomist' FK or
        # indirectly through a 'phlebotomist__user' chain.
        if not (request.user and request.user.is_authenticated):
            return False

        # Direct FK: obj.phlebotomist == phlebotomist profile
        if hasattr(obj, 'phlebotomist'):
            try:
                return obj.phlebotomist == request.user.phlebotomist_profile
            except Exception:
                return False

        # Direct user FK: obj.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Fallback: obj itself is the user
        return obj == request.user


class IsApprovedClient(BasePermission):
    message = "Access denied. You are not an approved client."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser or request.user.role == 'admin':
            return False
        if request.user.role != 'client':
            return False
        if not request.user.is_active:
            return False
        if request.user.suspended:
            self.message = "Access denied. Your account has been suspended."
            return False
        try:
            return request.user.client_profile.is_approved is True
        except Exception:
            return False

    def has_object_permission(self, request, view, obj):
        # The object must belong to the requesting client.
        if not (request.user and request.user.is_authenticated):
            return False

        # Direct FK: obj.client == client profile
        if hasattr(obj, 'client'):
            try:
                return obj.client == request.user.client_profile
            except Exception:
                return False

        # Direct user FK: obj.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Fallback: obj itself is the user
        return obj == request.user
