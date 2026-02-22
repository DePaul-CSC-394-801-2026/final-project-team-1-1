from django.shortcuts import render
import uuid

def ui_dashboard(request):
    """Premium Dashboard Implementation with Mock Data"""
    mock_rooms = [
        {"name": "Master Suite", "assets": {"count": 6}},
        {"name": "Chef's Kitchen", "assets": {"count": 12}},
        {"name": "Living Room", "assets": {"count": 4}},
        {"name": "Garage", "assets": {"count": 8}},
    ]
    return render(request, "ui/dashboard.html", {"rooms": mock_rooms})

def ui_home_setup(request):
    """Premium Home Setup Implementation"""
    mock_rooms = [
        {"name": "Master Suite", "assets": {"count": 6}},
        {"name": "Chef's Kitchen", "assets": {"count": 12}},
    ]
    return render(request, "ui/home_setup.html", {"rooms": mock_rooms})

def ui_appliances(request):
    """Premium Appliances Implementation"""
    return render(request, "ui/appliances.html")

def ui_appliance_detail(request, id):
    """Premium Appliance Detail Prototype"""
    return render(request, "ui/appliance_detail.html", {"id": id})
