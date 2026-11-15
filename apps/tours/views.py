from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# The Matterport "space" shown on the tour page. Not a secret: it is the public
# share link. To show a different space, change the id after `m=`.
MATTERPORT_TOUR_URL = "https://my.matterport.com/show/?m=Z6N6h2BYaxU"


@login_required
def tour(request):
    """Embedded 3D facility walkthrough. Any signed-in employee may view it;
    there is no per-user data here, so no finer-grained permission applies."""
    return render(request, "tours/tour.html", {"tour_url": MATTERPORT_TOUR_URL})
