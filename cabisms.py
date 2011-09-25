
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import math
import urllib, urllib2
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

CABI_URL = "http://www.capitalbikeshare.com/stations/bikeStations.xml"
GMAPS_URL = "https://maps.googleapis.com/maps/api/geocode/xml?"

class MainPage(webapp.RequestHandler):
    def get(self):

        # Get input address parameter value.
        input = self.request.get("address")

        # Geocode the input address.
        lat, long = gmaps_geocode(input)

        if lat == 0 and long == 0:
            output = "Address \"%s\" not found. Please try again." % (input)
        else:
            # Find the nearest CaBi stations
            output = find_stations(lat, long)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(output)

application = webapp.WSGIApplication(
                                     [('/', MainPage)],
                                     debug=True)

def gmaps_geocode(address, appended_dc=0):

    args = urllib.urlencode({"address": address, "sensor": "false"})
    f = urllib2.urlopen(GMAPS_URL+args)
    xml = f.read()

    soup = BeautifulStoneSoup(xml, 
                              convertEntities=BeautifulStoneSoup.HTML_ENTITIES)

    # Check that API lookup was OK.
    if soup("status")[0].text != "OK":
        return 0, 0

    # Find the location in DC or VA.
    found = 0
    for result in soup("result"):
        for component in result("address_component"):
            short_name = component.short_name.text
            if short_name == "DC" or short_name == "VA":
                found = 1
        if found:
            break

    if not found:
        if appended_dc:
            return 0, 0
        else:
            # Try appending DC to the address.
            return gmaps_geocode(address+" DC", 1)


    lat = float(result.geometry.lat.text)
    long = float(result.geometry.lng.text)

    return lat, long

def find_stations(lat_in, long_in):

    # Grab latest CaBi XML feed.
    f = urllib2.urlopen(CABI_URL)
    xml = f.read()
    soup = BeautifulStoneSoup(xml, 
                              convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
    stations = soup("station")

    station_list = []

    # Calculate distance to all stations, append station tuple to the list.
    for station in stations:
        locked = station.locked.text
        temporary = station.temporary.text
        installed = station.installed.text

        # Ignore locked, temporary and uninstalled stations.
        if locked == "true" or temporary == "true" or installed == "false":
            continue
        
        id = int(station.id.text)
        name = station.find("name").text
        lat_station = float(station.lat.text)
        long_station = float(station.long.text)
        bikes = int(station.nbbikes.text)
        docks = int(station.nbemptydocks.text)
        distance = calculate_distance(lat_in, long_in, 
                                      lat_station, long_station)

        station_list.append((distance, id, name, bikes, docks))

    # Sort station by distance
    station_list.sort()

    # Create the output
    outstr = ""
    n = 1
    for station in station_list[0:2]:
        distance, id, name, bikes, docks = station
        outstr += "%d. %s. %d bikes, %d docks\n" % (n, name, bikes, docks)
        n += 1
    outstr = outstr[:-1]

    return outstr


def calculate_distance(lat1, long1, lat2, long2):
    # Public domain code, found at:
    #  http://www.johndcook.com/python_longitude_latitude.html

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc    


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
