from django.shortcuts import render
from django.db.models import Q
from pages.models import DIYProject


# When user clicks search, the query is the value of the key value pair search:value. First, before it processes the query, it checks if the query is empty. If it is, it returns an empty list of projects. If it is not, it searches in title, description, and materials for the query.
# The search is case-insensitive and uses the icontains lookup.
# The results are then rendered in the search-results.html template.
def search_results_view(request):
    query = request.GET.get('search', '')
    projects = []
    
    if query:
        # Might have to adjust the way I did this. To avoid having to look up the exact title, I used Q objects and
        # used icontains to search in title, description, and materials. i meaning case-insensitive and partial match (wood would still find wooden table or whatever) - james
        projects = DIYProject.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(materials_json__icontains=query)
        )

    #whatever is found, it sends the projects list and the query to the search-results.html template to be displayed
    return render(request, "search-results.html", {
        'projects': projects,
        'query': query
    })

def project_page_view(request, project_id):
    project = DIYProject.objects.get(id=project_id)
    return render(request, "project-page.html", {"project": project})