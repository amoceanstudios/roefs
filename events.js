/* Gedelegeerde UI-acties. Geen eval, Function of uitvoerbare HTML-eventattributen.
   Alleen expliciet geregistreerde acties, letterlijke argumenten en vaste UI-context. */
const ROEFS_ACTIONS = new Set('analyze,caoCalculate,caoCheckContract,caoCheckSickness,caoCheckTravel,chooseRole,closeMobileMenu,closeModal,createUser,deleteRecord,editAccount,editPermissions,editRecord,endTour,exportCSV,goBack,hrAddTerm,hrDeleteTerm,hrPreview,hrSaveProfile,linkUser,loadPilotForm,login,logout,openPage,openShiftDetails,pilotDecide,pilotPropose,planCandidate,planMove,planNew,planSuggest,readMessage,refreshSmart,renderContent,saveAccount,saveLink,savePermissions,saveRecord,sendMessage,showShiftList,sosAssign,sosSearch,startTour,syncEdit,syncResolveForm,syncResolveSave,syncSave,syncSchedule,toggleMobileMenu,tourMove,v5AddCheck,v5Assign,v5AssignSave,v5Calendar,v5Check,v5Download,v5DownloadList,v5Drop,v5Edit,v5HomeDrill,v5HomeNew,v5Import,v5ImportSave,v5Invoice,v5InvoiceAction,v5InvoiceActionSave,v5MfaEnable,v5MfaSetup,v5NotificationPreference,v5Prepare,v5PrepareSave,v5Read,v5Reminders,v5Repeat,v5RepeatSave,v5Reports,v5Resize,v5ReviewHours,v5ReviewHoursSave,v5Revoke,v5SaveEntity,v5Search,v5Security,v5Select,v5SettingsSave,v5ShiftForm,v5ShiftSave,v5SkipTour,v5TimeForm,v5TimeSave,v5Timeline,v5TransitionForm,v5TransitionSave,v5Undo,v5Upload,v5UploadSave,v5Work,v5Workspace,v6Audit,v6ClockFinish,v6ClockFinishSave,v6ClockForm,v6ClockStart,v6DeleteFile,v6DeleteFileSave,v6Labor,v6LaborSave,v6Numbering,v6NumberingSave,v6Rescan,v6RetryForm,v6RetrySave,v6RotateRecovery,v6Series,v6SeriesChange,v6SeriesChangeSave,v6SeriesForm,v6SeriesSave'.split(','));
function roefsArguments(source,event,element){
 const values=[];let i=0;
 while(i<source.length){
  while(/\s/.test(source[i]||'')&&i<source.length)i++;
  if(i===source.length)break;
  let value;
  if(source[i]==="'"||source[i]==='"'){
   const quote=source[i++];let text='',closed=false;
   while(i<source.length){const ch=source[i++];if(ch===quote){closed=true;break}if(ch==='\\'){const escaped=source[i++];if(escaped==='u'){const hex=source.slice(i,i+4);if(!/^[a-fA-F0-9]{4}$/.test(hex))throw Error('Ongeldig tekstargument');text+=String.fromCharCode(parseInt(hex,16));i+=4}else{text+=({n:'\n',r:'\r',t:'\t',b:'\b',f:'\f'})[escaped]??escaped}}else text+=ch}
   if(!closed)throw Error('Onvolledig tekstargument');value=text;
   if(source.slice(i).startsWith('+v5ReportQuery')){value+=v5ReportQuery;i+='+v5ReportQuery'.length}
  }else{
   let end=source.indexOf(',',i);if(end<0)end=source.length;const token=source.slice(i,end).trim();i=end;
   if(/^-?\d+(\.\d+)?$/.test(token))value=Number(token);
   else if(token==='true'||token==='false')value=token==='true';
   else if(token==='null')value=null;
   else if(token==='event')value=event;
   else if(token==='this')value=element;
   else if(token==='this.checked')value=element.checked;
   else if(token==='this.value')value=element.value;
   else if(token==='this.form')value=element.form;
   else throw Error('Niet-ondersteund actieargument');
  }
  values.push(value);while(i<source.length&&/\s/.test(source[i]))i++;
  if(i<source.length){if(source[i++]!==',')throw Error('Ongeldige actiescheiding')}
 }
 return values;
}
function roefsAction(source,event,element){
 const exact={
  "event.preventDefault()":()=>event.preventDefault(),
  "if(event.key==='Enter')v5Search()":()=>{if(event.key==='Enter'){event.preventDefault();return v5Search()}},
  "filter=this.value;renderContent()":()=>{filter=element.value;return renderContent()},
  "selectedHr=Number(this.value);renderContent()":()=>{selectedHr=Number(element.value);return renderContent()},
  "plannerDate=this.value;openPage('shifts')":()=>{plannerDate=element.value;return openPage('shifts')},
  "plannerDate=this.value;v5Calendar()":()=>{plannerDate=element.value;return v5Calendar()},
  "v5group=this.value;v5Calendar()":()=>{v5group=element.value;return v5Calendar()},
  "v5period=this.value;v5Calendar()":()=>{v5period=element.value;return v5Calendar()},
  "v5offset+=25;v5Workspace()":()=>{v5offset+=25;return v5Workspace()},
  "v5offset-=25;v5Workspace()":()=>{v5offset-=25;return v5Workspace()}
 };
 if(Object.hasOwn(exact,source))return exact[source]();
 if(source.startsWith('event.dataTransfer.setData(')&&source.endsWith(')')){const args=roefsArguments(source.slice(27,-1),event,element);if(args.length!==2||args[0]!=='text/plain')throw Error('Ongeldige sleepactie');return event.dataTransfer.setData(...args)}
 const call=/^([A-Za-z]\w*)\((.*)\)$/.exec(source);
 if(!call||!ROEFS_ACTIONS.has(call[1])||typeof window[call[1]]!=='function')throw Error('Onbekende interfaceactie');
 return window[call[1]](...roefsArguments(call[2],event,element));
}
for(const type of ['click','change','submit','keydown','input','dragstart','dragover','drop','blur','focus']){
 document.addEventListener(type,event=>{
  const element=event.target.closest?.('[data-roefs-'+type+']');if(!element||element.disabled)return;
  if(type==='submit')event.preventDefault();
  try{const result=roefsAction(element.getAttribute('data-roefs-'+type),event,element);if(result?.catch)result.catch(error=>toast(error.message))}catch(error){toast('Actie kon niet worden uitgevoerd: '+error.message)}
 },true);
}

for(const action of ['v6Contract','v6ContractLocations','v6ContractLocationsSave','v6ContractDecision','v6ContractDecisionSave'])ROEFS_ACTIONS.add(action);

ROEFS_ACTIONS.add('v6ManagementDownload');

for(const action of ['v6LegacyPage','v6LegacySearch'])ROEFS_ACTIONS.add(action);

ROEFS_ACTIONS.add('v6RetentionToggle');

for(const action of ['v6ResizeDialog','v6ResizePreview','v6ResizeSave'])ROEFS_ACTIONS.add(action);
for(const action of ['v6Services','v6ServiceForm','v6ServiceSave','v6ServiceGenerateForm','v6ServiceGenerate','v6SchoolDemo'])ROEFS_ACTIONS.add(action);
for(const action of ['v6CustomerCase','v6CustomerCaseSave','v6CaseCalendar'])ROEFS_ACTIONS.add(action);
for(const action of ['v6MigrationHome','v6MigrationNew','v6MigrationCategory','v6MigrationTemplate','v6MigrationUpload','v6MigrationView','v6MigrationPreview','v6MigrationConfirm','v6MigrationResume','v6MigrationStop'])ROEFS_ACTIONS.add(action);
for(const action of ['v6Onboarding','v6OnboardingEdit','v6OnboardingSave'])ROEFS_ACTIONS.add(action);
for(const action of ['v6Accounting','v6AccountingSave','v6AccountingAction','v6AccountingQueue','v6AccountingRetry','v6Scopes','v6ScopeEdit','v6ScopeSave','v6Classify'])ROEFS_ACTIONS.add(action);
