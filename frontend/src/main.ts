import {createApp} from 'vue';
import PrimeVue from 'primevue/config';
import {definePreset} from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import App from './App.vue';
import './style.css';
const Storybook=definePreset(Aura,{semantic:{primary:{50:'#f0f6f0',100:'#dceadc',200:'#b9d5be',300:'#8ab89b',400:'#5d9378',500:'#386f59',600:'#255c4c',700:'#1d4c3e',800:'#193d33',900:'#17342c',950:'#0a1e18'}}});
createApp(App).use(PrimeVue,{theme:{preset:Storybook,options:{darkModeSelector:'.dark'}}}).mount('#app');
