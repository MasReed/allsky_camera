import sys
import time
import numpy as np
from subprocess import call
from argparse import ArgumentParser
import matplotlib.pyplot as plt
import astropy.fits.io as pyfits
from matplotlib import gridspec
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.units as u
from astropy.time import Time
from scipy.optimize import curve_fit, leastsq, least_squares

#-------------------
import conversions


# -------  constants ---------
HORIZON = 15
MAG_LIM = 3.


#load the test image
def raw_fits(filename):
    #returns FITS header and data
    if filename.lower().endswith(('.fits', '.fit')):
        f = pyfits.open(filename)
        h = f[0].header
        d = f[0].data
        f.close()
        return h, d
    else:
        raise Exception('Invalid Filetype')


#------------ THE ALLSKY PIPELINE ------------

def pipe(fname, verbose=True, grid=True, names=True, points=False, save=False):
	#open the image
	head, im = rawFits(fname)
	#im = np.rot90(im,1)

	#store the utc time of the obervation, iowa city lat and long
	time_str = head['date-obs']
	#time = '2018-04-18T08:17:33.591'
	print time_str
	time = Time(time_str) - 1*u.hour
	lst = conversions.utc_to_lst(time_str) - (1./24 * 360)

	#open the catalog
	star_catalog = np.load('star_catalog.npy')
	#print star_catalog[0]
	#iowa_city = EarthLocation(lat=41.6611*u.deg, lon=-1*91.5302*u.deg,height=50.*u.m)

	#using time, lat, and long, convert ra, dec to alt,az
	#alt_az catalog
	sky_cat = []
	for kk,star in enumerate(star_catalog):
		name, star_type, ra, dec, mag, epoch = star
		ra = float(ra); dec = float(dec); mag = float(mag)
		#c = SkyCoord(ra, dec, unit='deg')
		#obj_altaz = c.transform_to(AltAz(obstime=time, location=iowa_city))
		#alt = float("{0.alt:.3}".format(obj_altaz).split()[0]); az = float("{0.az:.3}".format(obj_altaz).split()[0]) 

		#convert ra, dec to alt, az 
		alt, az = conversions.radec_to_altaz(ra, dec, lst,debug=False)
		if alt > HORIZON and mag < MAG_LIM:
			#convert alt,az to x,y using Mason's fit
			x,y = conversions.altaz_to_xy(alt, az)
			sky_cat.append( [name, x,y, alt, az, ra, dec, mag] )


	fig, ax = plt.subplots(figsize=(4,6))
	ax.imshow(1*np.sqrt(im), origin='lower',cmap='gray',vmin=.4*np.max(np.sqrt(im)), vmax=1*np.max(np.sqrt(im)))
	#plot objects with names
	for kk, obj in enumerate(sky_cat):
		name = obj[0]; x = obj[1]; y = obj[2]
		if points:
			ax.scatter(y,x,marker='*',color='cyan',alpha=0.5)
		if names:
			ax.text(y,x,name, fontsize=5,alpha=0.9, color='gray')

	
	#plot alt,az grid (flag for ra,dec grid)
	if grid:
		circs, lines = conversions.altaz_grid(im, spacing=15, verbose=False)

		for c in circs:
				ax.add_patch(c)

		for l in lines:
			ax.plot( l[0],l[1],alpha=0.2,color='red')

	ax.set_xlim([0,480])
	ax.set_ylim([0,640])
	plt.axis('off')
	fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
	if verbose:
		plt.show()

	#compare to see where nearest stars are
	for kk, obj in enumerate(sky_cat):
		x = obj[1]; y = obj[2]
		try:
			yc,xc = conversions.centroid(np.power(im,2.),x,y,s=20, verbose=False)
		except:
			print

	#flag for image analysis -- edges, brightness, difference?

	#save as a new file
	if save:
		plt.savefig(outname, bbinches='tight')

	'''plt.close()
	fig,ax = plt.subplots(2)
	ax[0].scatter([x[3] for x in sky_cat], [x[5] for x in sky_cat])
	ax[1].scatter([x[4] for x in sky_cat], [x[6] for x in sky_cat])
	plt.show()'''

def errfunc(p, *args):
	a,b,c,d = p
	im, star_catalog, time = args
	#star_catalog, time = args
	#using time, lat, and long, convert ra, dec to alt,az
	#alt_az catalog
	sky_cat = []
	for kk,star in enumerate(star_catalog):
		name, star_type, ra, dec, mag, epoch = star
		ra = float(ra); dec = float(dec); mag = float(mag)

		#convert ra, dec to alt, az 
		alt, az = conversions.radec_to_altaz(ra, dec, time,debug=False)
		if alt > HORIZON and mag < MAG_LIM:
			#convert alt,az to x,y using Mason's fit
			x,y = conversions.altaz_to_xy(alt, az, pxpdeg=a, b= b, imgcenter=(c,d))
			print x, y
			sky_cat.append( [name, x,y, alt, az, ra, dec, mag] )
	
	#compute the distance from each predicted star to the nearest centroid
	chi2 = 0
	for kk, obj in enumerate(sky_cat):
		x = obj[1]; y = obj[2]
		try:
			yc,xc = conversions.centroid(im,x,y,s=30, verbose=False)
			chi2 += np.power( x-xc,2. ) + np.power(y-yc,2.)
		except:
			print x,y
			return 30
	chi2 = chi2 / len(sky_cat)
	return np.ones(4)*chi2




def min_distances(fname):
	head, im = rawFits(fname)
	#im = np.rot90(im,1)

	#store the utc time of the obervation, iowa city lat and long
	time = head['date-obs']
	
	#open the catalog
	star_catalog = np.load('star_catalog.npy')

	p0 = [-3.3, 0, 320., 240.]
	x = np.arange(480)
	y = np.arange(640)
	xv,yv = np.meshgrid(x,y)
	#p, cov = curve_fit(errfunc, (xv,yv), im, p0, args=(star_catalog, time))
	res = leastsq( errfunc, p0, args=(im,star_catalog, time) )

	print res

	




if __name__ == '__main__':
	fname = './assets/075318.FIT'
	#fname = './assets/clear_with_shield.FIT'
	pipe(fname, grid=True,points=False,names=True,verbose=True)
	#min_distances('./assets/clear_with_shield.FIT')





