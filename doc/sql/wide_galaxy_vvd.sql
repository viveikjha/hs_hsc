SELECT 
	f.object_id, f.ra, f.dec, f.tract, f.patch, f.parent_id, 
	f.a_g, f.a_r, f.a_i, f.a_z, f.a_y,                                   -- Basic information
	
	z.specz_id, z.specz_redshift, z.specz_redshift_err,                  -- Spec-z information when available
	
	-- Photometry 
	f.gmag_psf, f.gmag_psf_err, f.rmag_psf, f.rmag_psf_err,              -- Forced PSF magnitudes
    f.imag_psf, f.imag_psf_err, f.zmag_psf, f.zmag_psf_err,    
	f.ymag_psf, f.ymag_psf_err,
	
	f.gmag_kron, f.gmag_kron_err, f.rmag_kron, f.rmag_kron_err,          -- Forced Kron magnitudes
	f.imag_kron, f.imag_kron_err, f.zmag_kron, f.zmag_kron_err,
	f.ymag_kron, f.ymag_kron_err,
	
    f.gflux_kron_radius, f.rflux_kron_radius,                            -- Kron radius
	f.iflux_kron_radius, f.zflux_kron_radius, 
	f.yflux_kron_radius, 
	
	f.gcmodel_exp_mag, f.gcmodel_exp_mag_err,                            -- cModel magnitudes
	f.gcmodel_dev_mag, f.gcmodel_dev_mag_err,
	f.gcmodel_mag, f.gcmodel_mag_err,

	f.rcmodel_exp_mag, f.rcmodel_exp_mag_err,
	f.rcmodel_dev_mag, f.rcmodel_dev_mag_err,
	f.rcmodel_mag, f.rcmodel_mag_err,

	f.icmodel_exp_mag, f.icmodel_exp_mag_err,
	f.icmodel_dev_mag, f.icmodel_dev_mag_err,
	f.icmodel_mag, f.icmodel_mag_err,

	f.zcmodel_exp_mag, f.zcmodel_exp_mag_err,
	f.zcmodel_dev_mag, f.zcmodel_dev_mag_err,
	f.zcmodel_mag, f.zcmodel_mag_err,

	f.ycmodel_exp_mag, f.ycmodel_exp_mag_err,
	f.ycmodel_dev_mag, f.ycmodel_dev_mag_err,
	f.ycmodel_mag, f.ycmodel_mag_err,
	
	m1.gcmodel_exp_mag as gcmodel_exp_mag_meas,                          -- Measured cModel photometry 
	m1.gcmodel_exp_mag_err as gcmodel_exp_mag_err_meas, 
	m1.rcmodel_exp_mag as rcmodel_exp_mag_meas, 
	m1.rcmodel_exp_mag_err as rcmodel_exp_mag_err_meas, 
	m1.icmodel_exp_mag as icmodel_exp_mag_meas, 
	m1.icmodel_exp_mag_err as icmodel_exp_mag_err_meas, 
	m1.zcmodel_exp_mag as zcmodel_exp_mag_meas, 
	m1.zcmodel_exp_mag_err as zcmodel_exp_mag_err_meas, 

	m1.gcmodel_dev_mag as gcmodel_dev_mag_meas,                           
	m1.gcmodel_dev_mag_err as gcmodel_dev_mag_err_meas, 
	m1.rcmodel_dev_mag as rcmodel_dev_mag_meas, 
	m1.rcmodel_dev_mag_err as rcmodel_dev_mag_err_meas, 
	m1.icmodel_dev_mag as icmodel_dev_mag_meas, 
	m1.icmodel_dev_mag_err as icmodel_dev_mag_err_meas, 
	m1.zcmodel_dev_mag as zcmodel_dev_mag_meas, 
	m1.zcmodel_dev_mag_err as zcmodel_dev_mag_err_meas, 
	
	m1.gcmodel_mag as gcmodel_mag_meas,                           
	m1.gcmodel_mag_err as gcmodel_mag_err_meas, 
	m1.rcmodel_mag as rcmodel_mag_meas, 
	m1.rcmodel_mag_err as rcmodel_mag_err_meas, 
	m1.icmodel_mag as icmodel_mag_meas, 
	m1.icmodel_mag_err as icmodel_mag_err_meas, 
	m1.zcmodel_mag as zcmodel_mag_meas, 
	m1.zcmodel_mag_err as zcmodel_mag_err_meas, 
	
    ab.gchild_flux_convolved_seeing,                                    -- Afterburner aperture photometry
    ab.gchild_mag_convolved_1_0, 
    ab.gchild_mag_convolved_1_1, 
    ab.gchild_mag_convolved_1_2, 
    ab.gchild_mag_convolved_2_0,
    ab.gchild_mag_convolved_2_1, 
    ab.gchild_mag_convolved_2_2, 
    ab.gparent_mag_convolved_1_0, 
    ab.gparent_mag_convolved_1_1, 
    ab.gparent_mag_convolved_1_2, 
    ab.gparent_mag_convolved_2_0,
    ab.gparent_mag_convolved_2_1, 
    ab.gparent_mag_convolved_2_2, 
    ab.gdetected_notjunk, 
    ab.gchild_flux_convolved_flag, 
    ab.gchild_flux_convolved_0_deconv, 
    ab.gchild_flux_convolved_1_deconv, 
    ab.gchild_flux_convolved_2_deconv,

    ab.rchild_flux_convolved_seeing, 
    ab.rchild_mag_convolved_1_0, 
    ab.rchild_mag_convolved_1_1, 
    ab.rchild_mag_convolved_1_2, 
    ab.rchild_mag_convolved_2_0,
    ab.rchild_mag_convolved_2_1, 
    ab.rchild_mag_convolved_2_2, 
    ab.rparent_mag_convolved_1_0, 
    ab.rparent_mag_convolved_1_1, 
    ab.rparent_mag_convolved_1_2, 
    ab.rparent_mag_convolved_2_0,
    ab.rparent_mag_convolved_2_1, 
    ab.rparent_mag_convolved_2_2, 
    ab.rdetected_notjunk, 
    ab.rchild_flux_convolved_flag, 
    ab.rchild_flux_convolved_0_deconv, 
    ab.rchild_flux_convolved_1_deconv, 
    ab.rchild_flux_convolved_2_deconv,

    ab.ichild_flux_convolved_seeing, 
    ab.ichild_mag_convolved_1_0, 
    ab.ichild_mag_convolved_1_1, 
    ab.ichild_mag_convolved_1_2, 
    ab.ichild_mag_convolved_2_0,
    ab.ichild_mag_convolved_2_1, 
    ab.ichild_mag_convolved_2_2, 
    ab.iparent_mag_convolved_1_0, 
    ab.iparent_mag_convolved_1_1, 
    ab.iparent_mag_convolved_1_2, 
    ab.iparent_mag_convolved_2_0,
    ab.iparent_mag_convolved_2_1, 
    ab.iparent_mag_convolved_2_2, 
    ab.idetected_notjunk, 
    ab.ichild_flux_convolved_flag, 
    ab.ichild_flux_convolved_0_deconv, 
    ab.ichild_flux_convolved_1_deconv, 
    ab.ichild_flux_convolved_2_deconv,

    ab.zchild_flux_convolved_seeing, 
    ab.zchild_mag_convolved_1_0, 
    ab.zchild_mag_convolved_1_1, 
    ab.zchild_mag_convolved_1_2, 
    ab.zchild_mag_convolved_2_0,
    ab.zchild_mag_convolved_2_1, 
    ab.zchild_mag_convolved_2_2, 
    ab.zparent_mag_convolved_1_0, 
    ab.zparent_mag_convolved_1_1, 
    ab.zparent_mag_convolved_1_2, 
    ab.zparent_mag_convolved_2_0,
    ab.zparent_mag_convolved_2_1, 
    ab.zparent_mag_convolved_2_2, 
    ab.zdetected_notjunk, 
    ab.zchild_flux_convolved_flag, 
    ab.zchild_flux_convolved_0_deconv, 
    ab.zchild_flux_convolved_1_deconv, 
    ab.zchild_flux_convolved_2_deconv,

    ab.ychild_flux_convolved_seeing, 
    ab.ychild_mag_convolved_1_0, 
    ab.ychild_mag_convolved_1_1, 
    ab.ychild_mag_convolved_1_2, 
    ab.ychild_mag_convolved_2_0,
    ab.ychild_mag_convolved_2_1, 
    ab.ychild_mag_convolved_2_2, 
    ab.yparent_mag_convolved_1_0, 
    ab.yparent_mag_convolved_1_1, 
    ab.yparent_mag_convolved_1_2, 
    ab.yparent_mag_convolved_2_0,
    ab.yparent_mag_convolved_2_1, 
    ab.yparent_mag_convolved_2_2, 
    ab.ydetected_notjunk, 
    ab.ychild_flux_convolved_flag, 
    ab.ychild_flux_convolved_0_deconv, 
    ab.ychild_flux_convolved_1_deconv, 
    ab.ychild_flux_convolved_2_deconv,

	-- Blendedness 
	m1.gblendedness_abs_flux, m1.rblendedness_abs_flux,                  -- Blendedness
	m1.iblendedness_abs_flux, m1.zblendedness_abs_flux, 
	m1.yblendedness_abs_flux,
	
	m1.gblendedness_flags, m1.rblendedness_flags,                        -- Deblending flags
	m1.iblendedness_flags, m1.zblendedness_flags, 
	m1.yblendedness_flags,
	
	-- Shape and structures
	f.gcmodel_fracdev, f.rcmodel_fracdev,                                -- fracDev 
	f.icmodel_fracdev, f.zcmodel_fracdev,
	
	m1.rcmodel_exp_ellipse_11,                                           -- cModel shapes
	m1.rcmodel_exp_ellipse_22, 
	m1.rcmodel_exp_ellipse_12, 
	m1.icmodel_exp_ellipse_11, 
	m1.icmodel_exp_ellipse_22, 
	m1.icmodel_exp_ellipse_12, 
	
	m1.rcmodel_dev_ellipse_11, 
	m1.rcmodel_dev_ellipse_22, 
	m1.rcmodel_dev_ellipse_12, 
	m1.icmodel_dev_ellipse_11, 
	m1.icmodel_dev_ellipse_22, 
	m1.icmodel_dev_ellipse_12, 
	
	m1.rcmodel_ellipse_11, 
	m1.rcmodel_ellipse_22, 
	m1.rcmodel_ellipse_12, 
	m1.icmodel_ellipse_11, 
	m1.icmodel_ellipse_22, 
	m1.icmodel_ellipse_12,

	-- Meta information 
	f.gcountinputs, f.rcountinputs, f.icountinputs,                      -- Count Inputs
	f.zcountinputs, f.ycountinputs,
	
	f.gclassification_extendedness,                                      -- Star/Galaxy separation
	f.rclassification_extendedness, 
	f.iclassification_extendedness, 
	f.zclassification_extendedness, 
	f.yclassification_extendedness, 
	
	-- Flags 
	f.gflux_psf_flags, f.rflux_psf_flags, f.iflux_psf_flags,             -- PSF magnitude flags
	f.zflux_psf_flags, f.yflux_psf_flags, 
	
	f.gflux_kron_flags, f.rflux_kron_flags, f.iflux_kron_flags,          -- Kron magnitude flags
	f.zflux_kron_flags, f.yflux_kron_flags,
	 
	f.gcmodel_exp_flux_flags, f.rcmodel_exp_flux_flags,                  -- cModel magnitude flags
	f.icmodel_exp_flux_flags, f.zcmodel_exp_flux_flags, 
	f.ycmodel_exp_flux_flags, 

	f.gcmodel_dev_flux_flags, f.rcmodel_dev_flux_flags, 
	f.icmodel_dev_flux_flags, f.zcmodel_dev_flux_flags, 
	f.ycmodel_dev_flux_flags, 

	f.gcmodel_flux_flags, f.rcmodel_flux_flags, 
	f.icmodel_flux_flags, f.zcmodel_flux_flags, 
	f.ycmodel_flux_flags, 
	
	f.gflags_pixel_edge, f.rflags_pixel_edge, f.iflags_pixel_edge,       -- Edge pixel flags
	f.zflags_pixel_edge, f.yflags_pixel_edge,
	
	f.gflags_pixel_interpolated_any, f.rflags_pixel_interpolated_any,    -- Pixel interpolation flags
	f.iflags_pixel_interpolated_any, f.zflags_pixel_interpolated_any, 
	f.yflags_pixel_interpolated_any,
	
	f.gflags_pixel_interpolated_center, 
	f.yflags_pixel_interpolated_center,
	
    f.gflags_pixel_saturated_any, f.rflags_pixel_saturated_any,          -- Pixel saturation flags
	f.iflags_pixel_saturated_any, f.zflags_pixel_saturated_any, 
	f.yflags_pixel_saturated_any,

	f.gflags_pixel_saturated_center, f.yflags_pixel_saturated_center,
	
    f.gflags_pixel_cr_any, f.rflags_pixel_cr_any,                        -- Cosmic Ray flags
	f.iflags_pixel_cr_any, f.zflags_pixel_cr_any, 
	f.yflags_pixel_cr_any,

	f.gflags_pixel_cr_center, f.yflags_pixel_cr_center,
	
	f.gflags_pixel_bad, f.yflags_pixel_bad,                              -- Bad pixel flags
	
	f.gflags_pixel_suspect_center, f.rflags_pixel_suspect_center,        -- Suspect pixel flags
	f.iflags_pixel_suspect_center, f.zflags_pixel_suspect_center, 
	f.yflags_pixel_suspect_center, 
	
	f.gflags_pixel_suspect_any, f.rflags_pixel_suspect_any,              
	f.iflags_pixel_suspect_any, f.zflags_pixel_suspect_any, 
	f.yflags_pixel_suspect_any, 

    f.gflags_pixel_clipped_any, f.rflags_pixel_clipped_any,              -- Clipped pixel flags
	f.iflags_pixel_clipped_any, f.zflags_pixel_clipped_any, 
	f.yflags_pixel_clipped_any,
	
	f.gflags_pixel_bright_object_center,                                 -- Bright object flags
	f.rflags_pixel_bright_object_center,  
	f.iflags_pixel_bright_object_center,  
	f.zflags_pixel_bright_object_center,  
	f.yflags_pixel_bright_object_center,  
	
	f.gflags_pixel_bright_object_any,  
	f.rflags_pixel_bright_object_any,  
	f.iflags_pixel_bright_object_any,  
	f.zflags_pixel_bright_object_any,  
	f.yflags_pixel_bright_object_any
	
	
FROM 

	s16a_wide.forced as f                                                -- Forced photometry catalog 
	
	LEFT JOIN s16a_wide.specz as z                                       -- Spec-z catalog
		USING (object_id)
	
	LEFT JOIN s16a_wide.afterburner as ab 								 -- After burner photometry catalog 
		USING (object_id)
	
	LEFT JOIN s16a_wide.meas as m1 										 -- Measurement catalog 1
		USING (object_id)
	
WHERE

	-- Region (VVDS)
	(f.tract IN (9206, 9207, 9208, 9209, 9210, 9211, 9212, 9213, 9214, 9215, 9216, 9217, 9218, 9219,
                 9448, 9449, 9450, 9451, 9452, 9453, 9454, 9455, 9456, 9457, 9458, 9459, 9460, 9461, 9462,
                 9691, 9692, 9693, 9694, 9695, 9696, 9697, 9698, 9699, 9700, 9701, 9702, 9703, 9704, 9705,
                 9933, 9934, 9935, 9936, 9937, 9938, 9939, 9940, 9941, 9942, 9943, 9944, 9945, 9946,
                 10176, 10177, 10178, 10179, 10180, 10181, 10182, 10183, 10184, 10185, 10186, 10187, 10188)) 
	
	-- Primary detection
    AND f.detect_is_primary = True     
	
	-- Deblending 
	AND f.deblend_nchild = 0  

	-- cModel magnitude / Kron magnitude cut
	AND (f.icmodel_mag <= 22.5 
		 OR 
		 f.imag_kron <= 22.5)
	
	-- cModel or Kron photometry is not failed
	AND (f.gcmodel_flux_flags is not True 
		 OR 
		 f.iflux_kron_flags is not True)
	
	-- i-band depth 
	AND f.icountinputs >= 3
	
	-- Extended objects
    AND f.iclassification_extendedness >= 0.10
	
	-- SDSS centroid 
	AND f.icentroid_sdss_flags is not True
	AND f.rcentroid_sdss_flags is not True
	AND f.gcentroid_sdss_flags is not True
	
	-- Central pixel is not interpolated
	AND f.rflags_pixel_interpolated_center is not True
	AND f.iflags_pixel_interpolated_center is not True
	AND f.zflags_pixel_interpolated_center is not True
	
	-- Central pixel is not saturated
	AND f.rflags_pixel_saturated_center is not True
	AND f.iflags_pixel_saturated_center is not True
	AND f.zflags_pixel_saturated_center is not True
	
	-- Central pixel is not bothered by Cosmic-ray
	AND f.rflags_pixel_cr_center is not True
	AND f.iflags_pixel_cr_center is not True
	AND f.zflags_pixel_cr_center is not True

	-- Central pixel is not bad
	AND f.rflags_pixel_bad is not True
	AND f.iflags_pixel_bad is not True
	AND f.zflags_pixel_bad is not True
	
	-- Object is not off image
	AND f.iflags_pixel_offimage is not True
