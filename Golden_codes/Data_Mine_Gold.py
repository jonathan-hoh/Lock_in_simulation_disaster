#!/usr/bin/env python
# coding: utf-8

# In[47]:


# Run parameter file to initialize packages, constants, functions, and timespacing
get_ipython().run_line_magic('run', 'C:/Users/hohjo/Documents/Doctoral_Work/Jarrahi_Work/lock_in_software_sim/Golden_Codes/Params_Gold.ipynb')

#%%
###############################################################################################
#                                                                                             #
#                                        Lock-in Simulation (100 Mhz Tone)                    #
#                                                                                             #
###############################################################################################

#***********************************#
############################        #
# User Inputs:             #        #
#    Channel and Run time  #        #
############################        #
chan = 20                           #
run_time = 50                       #
#***********************************#
        
    # Define how many seconds of data should be simulated and how many accumulations are required

num_accum = int(run_time * (1/accum_time)) # number of total accumulations in simulation time

    # create file name for saving data in csv if desired

file_name = '%d_sec_lockin_sim_gold_bincompare.csv'%(run_time)   

    #Make an empty array to be filled with accumulations

raw_lock_accums_i = np.zeros((num_accum, FFT_length))
raw_lock_accums_q = np.zeros((num_accum, FFT_length))
raw_intnsty = np.zeros((num_accum, FFT_length))
n_raw_lock_accums_i = np.zeros((num_accum, FFT_length))
n_raw_lock_accums_q = np.zeros((num_accum, FFT_length))
n_raw_intnsty = np.zeros((num_accum, FFT_length))

filt_accums_i = np.zeros((num_accum, FFT_length))
filt_accums_q = np.zeros((num_accum, FFT_length))
final_intsty_out = np.zeros((num_accum, FFT_length))
n_filt_accums_i = np.zeros((num_accum, FFT_length))
n_filt_accums_q = np.zeros((num_accum, FFT_length))
n_final_intsty_out = np.zeros((num_accum, FFT_length))


#***********************************#
#                                   #
#           Creating Time           #        
#                                   #
#***********************************#

for i in range(num_accum):
    print('we are on accumulation number %d out of %d'%(i+1, num_accum))

        ##### Create an array with the times of the FFT frames #####

    frame_times = np.linspace(i * frame_time, i * frame_time + (accum_frames-1) * frame_time, (accum_frames)  )

        ############################################################################################################    
        # Create an array of times that will be used to create the "pieces" of the wave                            #  
        # Populate time array with lengths to be used later                                                        #
        # This is an absolutely crazy vectorization of a previous loop I had, but it runs 100 times faster. Sorry. #
        ############################################################################################################

    timespace = np.linspace(np.linspace(frame_times[0], frame_times[1], FFT_length), 
                            np.linspace(frame_times[accum_frames-2], frame_times[accum_frames-1], FFT_length),
                            num = accum_frames-2)


#***********************************#
#                                   #
#            Signals                #
#   (Creation and Timestreaming)    #
#                                   #
#***********************************#

        # tone of interest
    signal = real_wave(1, source_freq, timespace)
    
    chop_sig = GET_TO_DA_CHOPPAH(signal, timespace)
    
            # Lets make some noiiissseeee
    
     ##### Now add some white noise #####
    w_noise = np.random.normal(0, .12, chop_sig.shape)
    
        ##### And some pink noise #####
    beta = 1                                            # the exponent for pink noise
    samples = signal.shape                               # number of samples to generate (mimic the dimensions of the signal)
    y = cn.powerlaw_psd_gaussian(beta, samples)
    
    noisy_sig = chop_sig + w_noise + y   
        
        # Now put the unchopped noise signal through PFB

    spectra = (np.fft.fft(chop_sig, n = FFT_length))*(2/FFT_length) 
    n_spectra = (np.fft.fft(noisy_sig, n = FFT_length))*(2/FFT_length)
        
        # Once again, take transpose of FFT matrix to get channel timestreams
    
    (t_streams, n_t_streams) = (np.transpose(spectra), np.transpose(n_spectra))
    (t_streams_i, n_t_streams_i) = (np.real(t_streams), np.real(n_t_streams))
    (t_streams_q, n_t_streams_q) = (np.imag(t_streams), np.imag(n_t_streams))
    
    (t_stream_mag, n_t_stream_mag) = (magnitude(t_streams_i, t_streams_q), magnitude(n_t_streams_i, n_t_streams_q))
   

    #########################################
    #    Mixing Channel Timestreams Down    #
    #########################################   

        # Create time array to control internally generated wave 

    timespace2 = np.linspace(i * frame_time, i * frame_time + (accum_frames-1) * frame_time, (accum_frames)-2)

        # Create generated signal inside FPGA at square wave frequency 

    sq_i =(sig.square(2 * np.pi * square_freq * timespace2)) 
    sq_q =(sig.square(2 * np.pi * square_freq * timespace2 + (np.pi/2)))    
            
        # Mix together timestreams and chops
    
    (downmix_i, downmix_q) = c_mult(t_stream_mag, 0, sq_i, sq_q)
    (n_downmix_i, n_downmix_q) = c_mult(n_t_stream_mag, 0, sq_i, sq_q)
    
    #(downmix_intsty, n_downmix_intsty) = (intensify(downmix_i, downmix_q), intensify(n_downmix_i, n_downmix_q))
     
          # For sanity checkse, lets pocket the unfiltered data (JFD!) #
    raw_accum_i = np.sum(downmix_i,1)
    n_raw_accum_i = np.sum(n_downmix_i,1)
    raw_accum_q = np.sum(downmix_q,1)
    n_raw_accum_q = np.sum(n_downmix_q,1)
    raw_intnsty_vec = intensify(downmix_i, downmix_q)
    n_raw_intnsty_vec = intensify(n_downmix_i, n_downmix_q)
    
    raw_lock_accums_i[i] = raw_accum_i 
    n_raw_lock_accums_i[i] = n_raw_accum_i
    raw_lock_accums_q[i] =  raw_accum_q
    n_raw_lock_accums_q[i] = n_raw_accum_q 
    raw_intnsty[i] = np.sum(raw_intnsty_vec, 1)
    n_raw_intnsty[i] = np.sum(n_raw_intnsty_vec, 1)
   
    ##### Filtering stage #####
   
    ((filt_mix_i, filt_mix_q), (n_filt_mix_i, n_filt_mix_q)) = (lowpass_i_q(downmix_i, downmix_q), lowpass_i_q(n_downmix_i, n_downmix_q))

        #### Accumulate I and Q separately (JFD!) ####
    (filt_accum_i, n_filt_accum_i) = (np.sum(filt_mix_i, 1), np.sum(n_filt_mix_i, 1))
    (filt_accum_q, n_filt_accum_q) = (np.sum(filt_mix_q, 1), np.sum(n_filt_mix_q, 1))
    filt_accums_i[i] = filt_accum_i
    n_filt_accums_i[i] = n_filt_accum_i
    filt_accums_q[i] =filt_accum_q
    n_filt_accums_q[i] = n_filt_accum_q
    
    #### Take filtered intensity ####
     
    (filt_intsty, n_filt_intsty) = (intensify(filt_mix_i, filt_mix_q), intensify(n_filt_mix_i, n_filt_mix_q))
    (intsty_accum, n_intsty_accum) = (np.sum(filt_intsty,1), np.sum(n_filt_intsty, 1))
    final_intsty_out[i] = intsty_accum 
    n_final_intsty_out[i] = n_intsty_accum

#%%

final_channel_ints = np.transpose(final_intsty_out)
n_final_channel_ints = np.transpose(n_final_intsty_out)


#%%
# =============================================================================
# Plotting accumulator values for BOI
# =============================================================================
filt_fig, (ax_i, ax_q) = plt.subplots(nrows=2, sharex=True, sharey=True) 
#ax_i.set_xlim(0,100)
ax_i.set_ylim(0, 9000)
filt_fig.suptitle('Accumulation Values at Output for B.O.I. (Modulated Input)')
ax_i.plot(final_channel_ints[chan])
ax_i.set_title('Noiseless Case')
ax_q.plot(n_final_channel_ints[chan])
ax_q.set_title('Noisy Case')


#%%
# =============================================================================
# Plotting accumulator values for adjacent bins
# =============================================================================
filt_fig, (ax_i, ax_q) = plt.subplots(nrows=2, sharex=True, sharey=True) 
#ax_i.set_xlim(0,100)
#ax_i.set_ylim(0, 9000)
filt_fig.suptitle('Accumulation Values at Output for Distant Bin (Modulated Input)')
ax_i.plot(final_channel_ints[chan+200])
ax_i.set_title('Noiseless Case')
ax_q.plot(n_final_channel_ints[chan+200])
ax_q.set_title('Noisy Case')
#%%

# =============================================================================
# Save data to files because otherwise we have to do this shit again
# =============================================================================


save_data('%d_sec_datamine_final_intsty_out.csv'%(run_time), final_channel_ints)
save_data('%d_sec_datamine_n_final_intsty_out.csv'%(run_time), n_final_channel_ints)
save_data('%d_sec_datamine_raw_intnsty.csv'%(run_time), raw_intnsty)
save_data('%d_sec_datamine_n_raw_intnsty.csv'%(run_time), n_raw_intnsty)
save_data('%d_sec_datamine_filt_accums_i.csv'%(run_time), filt_accums_i)
save_data('%d_sec_datamine_filt_accums_q.csv'%(run_time), filt_accums_q)
save_data('%d_sec_datamine_n_filt_accums_i.csv'%(run_time), n_filt_accums_i)
save_data('%d_sec_datamine_n_filt_accums_q.csv'%(run_time), n_filt_accums_q)
#%%

# =============================================================================
# Making Plots
# =============================================================================

# Filtered accumulation data in
plt.plot(filt_accums_i)
plt.plot(filt_accum_q)






















#%%
# =============================================================================
# Making plots
# =============================================================================

# Filtered accumulation real and imag

filt_fig, (ax_i, ax_q) = plt.subplots(nrows=2, sharex=True) 
#ax_i.set_xlim(0,100)
filt_fig.suptitle('Filtered Accumulator Integrations (Modulated Input, Noiseless)')
ax_i.plot((np.transpose(filt_accums_i))[chan])
ax_i.set_title('Real Component')
ax_q.plot((np.transpose(filt_accums_q))[chan])
ax_q.set_title('Imaginary Component')


#%%

filt_fig, (ax_i, ax_q) = plt.subplots(nrows=2, sharex=True) 
#ax_i.set_xlim(0,100)
filt_fig.suptitle('Filtered Accumulator Integrations (Modulated Input, Noisy)')
ax_i.plot((np.transpose(n_filt_accums_i))[chan])
ax_i.set_title('Real Component')
ax_q.plot((np.transpose(n_filt_accums_q))[chan])
ax_q.set_title('Imaginary Component')

#%%
# =============================================================================
# Plotting Final Results for bin of interest
# =============================================================================
output_fig, (ax_1, ax_2) = plt.subplots(nrows=2, sharex=True)
output_fig.suptitle('Final Intensity Accumulation Integrations (Modulated Input)')
ax_1.plot(final_intsty_out[:,chan])
ax_1.set_title('Noiseless Simulation')
ax_2.plot(n_final_intsty_out[:,chan])
ax_2.set_title('Noisy Simulation')


#%%
# =============================================================================
# Plotting Final Results for Bins directly adjacent to BOI
# =============================================================================

output_fig_adj, (ax_1_adj, ax_2_adj) = plt.subplots(nrows=2, sharex=True)
output_fig_adj.suptitle('Final Intensity Accumulation Integrations (Adjacent Bin) (Modulated Input)')
ax_1_adj.plot(final_intsty_out[:,chan-1])
ax_1_adj.set_title('Noiseless Simulation')
ax_2_adj.plot(n_final_intsty_out[:,chan-1])
ax_2_adj.set_title('Noisy Simulation')

#%%

output_fig_adj, (ax_1_adj, ax_2_adj) = plt.subplots(nrows=2, sharex=True)
output_fig_adj.suptitle('LPF Output at bin of interest')
ax_1_adj.plot(filt_mix_i[chan])
ax_1_adj.set_title('Real Component')
ax_2_adj.plot(filt_mix_q[chan])
ax_2_adj.set_title('Imaginary Component')

#%%

output_fig_adj, (ax_1_adj, ax_2_adj) = plt.subplots(nrows=2, sharex=True)
output_fig_adj.suptitle('LPF Output at bin of interest (Noisy)')
ax_1_adj.plot(n_filt_mix_i[chan])
ax_1_adj.set_title('Real Component')
ax_2_adj.plot(n_filt_mix_q[chan])
ax_2_adj.set_title('Imaginary Component')

#%%
# =============================================================================
# Extra Fun Zone
# =============================================================================

flat_sig = signal.flatten()
flat_chop = chop_sig.flatten()
#flat_chop = choppa_signal.flatten()
vec_len = np.shape(flat_chop)[0]
vec_len_2 = vec_len/1024
plt.plot(samp_2_sec_2(np.arange(0,vec_len)),flat_chop)
plt.xlim(0,5000000/(25*10**6))
plt.ticklabel_format(axis="x", style="sci", scilimits=(0,0))
plt.title('Bin of Interest FFT Output Timestream Intensity' )
plt.xlabel('Time(seconds)')
plt.ylabel('Intensity')
